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
    # icônes G2 (10/10/2026) : le pictogramme du rail est la clé de la suite « Deepotus Glyph »
    assert 'edition: "dz-nav-cf-edition"' in core, "le rail a son pictogramme"


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


# ─────────────────────── PR B : Tabletop Simulator ──────────────────────────
# Relu le 04/10/2026 : planche 4096 px au plus (kb.tabletopsimulator.com/custom-content/asset-creation), grille
# NumWidth x NumHeight sans maximum publié (10 x 7 = convention : 70 cases, la dernière sert de carte cachée SAUF
# avec BackIsHidden), objet JSON CustomDeck {FaceURL, BackURL, NumWidth, NumHeight, BackIsHidden, UniqueBack}
# (save-file-format), CardID = 100 x clé de deck + index (relevé sur des objets sauvegardés, pas publié : DIT).
# DÉCISION DE L'UTILISATEUR (04/10) : chemins locaux file:/// + ZIP, ET copie dans Saved Objects.
import io                                                        # noqa: E402
import json                                                      # noqa: E402
import zipfile                                                   # noqa: E402
from PIL import Image                                            # noqa: E402

TTS_DIR = pathlib.Path(_tmp, "Documents", "My Games", "Tabletop Simulator", "Saves", "Saved Objects")
os.environ["DEEPOTUS_TTS_DIR"] = str(TTS_DIR)


def _carte(w, h, rgb, bord=(255, 255, 255), fond_perdu=37):
    """Une carte dont le FOND PERDU est d'une autre couleur : on voit si la coupe tombe juste."""
    im = Image.new("RGB", (w, h), bord)
    im.paste(Image.new("RGB", (w - 2 * fond_perdu, h - 2 * fond_perdu), rgb), (fond_perdu, fond_perdu))
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def _tts(n=3, fmt="poker_us", backs="meme", px=None, noms=None, nom_jeu="Banc TTS", poser=False):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": nom_jeu})
            did = r.json()["deck"]["id"]
            await c.patch(f"/api/cards/{did}", json={"format": {"fmt": fmt, "dpi": 300}})
            g = CT.geom(fmt, 300)
            w, h = px or g.canvas_px
            bo = int(round(g.bleed_off_px[0]))
            files = [("fronts", (f"f{i}.png", _carte(w, h, (10 + i, 100, 200), fond_perdu=bo), "image/png")) for i in range(n)]
            if backs == "meme":
                files += [("backs", (f"b{i}.png", _carte(w, h, (200, 50, 50), fond_perdu=bo), "image/png")) for i in range(n)]
            elif backs == "un-de-moins":
                files += [("backs", (f"b{i}.png", _carte(w, h, (200, 50, 50 + i), fond_perdu=bo), "image/png")) for i in range(n - 1)]
            elif backs == "uniques":
                files += [("backs", (f"b{i}.png", _carte(w, h, (200, 50 + i, 50), fond_perdu=bo), "image/png")) for i in range(n)]
            spec = {"noms": noms if noms is not None else [f"Carte {i + 1}" for i in range(n)]}
            r = await c.post(f"/api/cards/{did}/edition/tts", data={"spec": json.dumps(spec)}, files=files, timeout=300.0)
            rp = await c.post(f"/api/cards/{did}/edition/tts/poser", json={}) if poser else None
            return r, rp, did
    return asyncio.run(go())


def _zip(r):
    z = zipfile.ZipFile(io.BytesIO(r.content))
    obj = json.loads(z.read([n for n in z.namelist() if n.endswith(".json") and "manifeste" not in n][0]).decode("utf-8"))
    return z, obj


def test_tts_la_planche_est_toujours_10x7_a_la_coupe_sous_4096():
    r, _, did = _tts(3)
    assert r.status_code == 200, r.text
    z, obj = _zip(r)
    faces = [n for n in z.namelist() if "/faces_" in n]
    assert len(faces) == 1, z.namelist()
    im = Image.open(io.BytesIO(z.read(faces[0]))).convert("RGB")
    # poker US : coupe 750 x 1050 -> cellule 409 x 573 (ratio de COUPE), planche TOUJOURS 10 x 7 (TTS découpe par sa grille)
    assert im.size == (4090, 4011), im.size
    # la COUPE : le fond perdu blanc a disparu, la carte 2 (case 1) est bleue jusqu'aux bords de sa case
    for xy in ((409 + 2, 2), (409 + 406, 570), (2, 2)):
        assert im.getpixel(xy)[2] > 170 and im.getpixel(xy)[0] < 60, (xy, im.getpixel(xy))
    assert sum(im.getpixel((409 * 5 + 200, 573 * 3 + 200))) > 700, "case vide"
    assert r.headers["X-CF-Cellule"] == "409x573" and r.headers["X-CF-Planches"] == "1" and r.headers["X-CF-Cartes"] == "3"


def test_tts_l_objet_sauvegarde_est_un_deck_aux_bons_identifiants():
    r, _, did = _tts(3, noms=["Gobelin", "Elfe", ""])
    z, obj = _zip(r)
    deck = obj["ObjectStates"][0]
    assert deck["Name"] == "Deck" and deck["Nickname"] == "Banc TTS"
    cd = deck["CustomDeck"]["1"]
    assert (cd["NumWidth"], cd["NumHeight"], cd["BackIsHidden"], cd["UniqueBack"]) == (10, 7, True, False), cd
    assert cd["FaceURL"].startswith("file:///") and cd["FaceURL"].endswith(".jpg")
    assert deck["DeckIDs"] == [100, 101, 102]
    cartes = deck["ContainedObjects"]
    assert [c["CardID"] for c in cartes] == [100, 101, 102] and [c["Name"] for c in cartes] == ["Card"] * 3
    assert [c["Nickname"] for c in cartes] == ["Gobelin", "Elfe", "Carte 3"]      # un nom vide ne part pas vide
    assert all(c["CustomDeck"]["1"] == cd for c in cartes)
    # LES CHEMINS MÈNENT À DES FICHIERS QUI EXISTENT SUR CE PC, identiques à ceux du ZIP
    face = pathlib.Path(cd["FaceURL"][len("file:///"):])
    assert face.is_file() and face.read_bytes() == z.read([n for n in z.namelist() if "/faces_" in n][0])
    assert pathlib.Path(cd["BackURL"][len("file:///"):]).is_file()


def test_tts_un_dos_commun_est_une_image_des_dos_differents_une_planche():
    r, _, _ = _tts(3, backs="meme")
    z, obj = _zip(r)
    assert not obj["ObjectStates"][0]["CustomDeck"]["1"]["UniqueBack"]
    dos = [n for n in z.namelist() if "/dos" in n]
    assert len(dos) == 1 and Image.open(io.BytesIO(z.read(dos[0]))).size == (409, 573), dos
    r, _, _ = _tts(3, backs="uniques")
    z, obj = _zip(r)
    cd = obj["ObjectStates"][0]["CustomDeck"]["1"]
    assert cd["UniqueBack"] is True
    dos = [n for n in z.namelist() if "/dos" in n]
    assert len(dos) == 1 and Image.open(io.BytesIO(z.read(dos[0]))).size == (4090, 4011)
    im = Image.open(io.BytesIO(z.read(dos[0]))).convert("RGB")
    assert abs(im.getpixel((409 * 2 + 200, 300))[1] - 52) <= 3, im.getpixel((409 * 2 + 200, 300))   # le dos 3 en case 3


def test_tts_sans_verso_un_dos_neutre_et_c_est_dit():
    r, _, _ = _tts(2, backs=None)
    assert r.status_code == 200, r.text
    z, obj = _zip(r)
    man = json.loads(z.read([n for n in z.namelist() if n.endswith("manifeste.json")][0]))
    assert "aucun verso" in man["dos"]


def test_tts_au_dela_de_70_cartes_une_seconde_planche_et_deux_cles():
    r, _, _ = _tts(72, backs=None)
    assert r.status_code == 200, r.text
    z, obj = _zip(r)
    deck = obj["ObjectStates"][0]
    assert sorted(deck["CustomDeck"]) == ["1", "2"]
    assert deck["DeckIDs"][:2] == [100, 101] and deck["DeckIDs"][69] == 169 and deck["DeckIDs"][70:] == [200, 201]
    assert r.headers["X-CF-Planches"] == "2"
    assert len([n for n in z.namelist() if "/faces_" in n]) == 2


def test_tts_un_verso_manquant_est_refuse_en_le_disant():
    r, _, _ = _tts(3, backs="un-de-moins")
    assert r.status_code == 400 and "2 verso(s) pour 3 recto(s)" in r.text, r.text


def test_tts_une_seule_carte_est_un_objet_carte():
    r, _, _ = _tts(1, backs=None)
    z, obj = _zip(r)
    assert obj["ObjectStates"][0]["Name"] == "Card" and obj["ObjectStates"][0]["CardID"] == 100


def test_tts_un_format_haut_tient_dans_4096():
    r, _, _ = _tts(2, fmt="tarot_us", backs=None)
    assert r.status_code == 200, r.text
    z, _ = _zip(r)
    im = Image.open(io.BytesIO(z.read([n for n in z.namelist() if "/faces_" in n][0])))
    # tarot US : coupe 825 x 1425 -> 409 de large ferait 7 x 706 = 4942 > 4096 : la HAUTEUR décide (585)
    assert max(im.size) <= 4096 and im.size == (3390, 7 * 585), im.size
    assert r.headers["X-CF-Cellule"] == "339x585", r.headers["X-CF-Cellule"]


def test_tts_un_bitmap_a_la_mauvaise_taille_est_refuse():
    r, _, _ = _tts(1, px=(822, 1122), backs=None)
    assert r.status_code == 400 and "822" in r.text and "825" in r.text, r.text
    r, _, _ = _tts(0, backs=None)
    assert r.status_code == 400 and "Aucune carte" in r.text, r.text


def test_tts_une_reexportation_change_le_nom_des_planches():
    """TTS garde en CACHE une image par URL : réexporter sous le même nom montrerait l'ancienne. Le nom porte
    l'empreinte du contenu, et le dossier ne garde que le dernier export."""
    r1, _, did = _tts(2, backs=None, nom_jeu="Cache")
    face1 = _zip(r1)[1]["ObjectStates"][0]["CustomDeck"]["1"]["FaceURL"]

    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            files = [("fronts", (f"f{i}.png", _carte(825, 1125, (250, 250, 0)), "image/png")) for i in range(2)]
            return await c.post(f"/api/cards/{did}/edition/tts", data={"spec": "{}"}, files=files, timeout=120.0)
    r2 = asyncio.run(go())
    assert r2.status_code == 200, r2.text
    face2 = _zip(r2)[1]["ObjectStates"][0]["CustomDeck"]["1"]["FaceURL"]
    assert face1 != face2 and not pathlib.Path(face1[8:]).exists() and pathlib.Path(face2[8:]).is_file()


def test_tts_poser_dans_saved_objects():
    import shutil
    racine_tts = TTS_DIR.parent.parent                    # « My Games/Tabletop Simulator »
    if racine_tts.exists():
        shutil.rmtree(racine_tts)
    r, rp, did = _tts(2, backs=None, nom_jeu="Pose", poser=True)
    assert rp.status_code == 409 and "Tabletop Simulator" in rp.text, rp.text          # TTS absent : dit
    racine_tts.mkdir(parents=True)
    r, rp, did = _tts(2, backs=None, nom_jeu="Pose", poser=True)
    assert rp.status_code == 200, rp.text
    js, th = TTS_DIR / "Deepotus" / "pose.json", TTS_DIR / "Deepotus" / "pose.png"
    assert js.is_file() and th.is_file() and json.loads(js.read_text(encoding="utf-8"))["ObjectStates"][0]["Name"] == "Deck"
    assert rp.json()["chemin"] == str(js)

    async def sans_export():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Rien"})
            return await c.post(f"/api/cards/{r.json()['deck']['id']}/edition/tts/poser", json={})
    r0 = asyncio.run(sans_export())
    assert r0.status_code == 409 and "Exportez" in r0.text, r0.text


# ─────────────────────── PR C : Tabletopia ──────────────────────────────────
# Relu le 04/10/2026 (help.tabletopia.com/knowledge-base/how-to-prepare-graphics) : JPEG ou PNG ; « Try not to
# exceed the image size of 2000x2000 pixels for each object » ; recto et verso dans des FICHIERS SÉPARÉS
# (« 52 front images and 1 back ») ; tous les composants d'un type à la MÊME taille ; 3-10 Mo au maximum, 1-2 visés.
def _tabletopia(n=3, fmt="poker_us", dpi=300, backs="meme", noms=None, nom_jeu="Banc Tabletopia"):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": nom_jeu})
            did = r.json()["deck"]["id"]
            await c.patch(f"/api/cards/{did}", json={"format": {"fmt": fmt, "dpi": dpi}})
            g = CT.geom(fmt, dpi)
            w, h = g.canvas_px
            bo = int(round(g.bleed_off_px[0]))
            files = [("fronts", (f"f{i}.png", _carte(w, h, (10 + i, 100, 200), fond_perdu=bo), "image/png")) for i in range(n)]
            if backs == "meme":
                files += [("backs", (f"b{i}.png", _carte(w, h, (200, 50, 50), fond_perdu=bo), "image/png")) for i in range(n)]
            elif backs == "uniques":
                files += [("backs", (f"b{i}.png", _carte(w, h, (200, 50 + 20 * i, 50), fond_perdu=bo), "image/png")) for i in range(n)]
            spec = {"noms": noms if noms is not None else [f"Carte {i + 1}" for i in range(n)]}
            return await c.post(f"/api/cards/{did}/edition/tabletopia", data={"spec": json.dumps(spec)}, files=files, timeout=300.0)
    return asyncio.run(go())


def test_tabletopia_une_image_par_face_a_la_coupe_sans_agrandir():
    r = _tabletopia(3)
    assert r.status_code == 200, r.text
    z = zipfile.ZipFile(io.BytesIO(r.content))
    noms = sorted(n for n in z.namelist() if n.endswith(".jpg"))
    assert noms == ["tabletopia/banc-tabletopia_01_recto.jpg", "tabletopia/banc-tabletopia_02_recto.jpg",
                    "tabletopia/banc-tabletopia_03_recto.jpg", "tabletopia/banc-tabletopia_dos.jpg"], noms
    for n in noms:
        im = Image.open(io.BytesIO(z.read(n))).convert("RGB")
        assert im.size == (750, 1050), (n, im.size)               # la COUPE, à 300 DPI : jamais agrandie
        assert im.getpixel((1, 1))[0] < 60 or "dos" in n, (n, im.getpixel((1, 1)))     # plus de fond perdu blanc
    assert Image.open(io.BytesIO(z.read("tabletopia/banc-tabletopia_02_recto.jpg"))).convert("RGB").getpixel((375, 525))[0] in range(8, 15)
    assert r.headers["X-CF-Px"] == "750x1050" and r.headers["X-CF-Fichiers"] == "4"


def test_tabletopia_le_manifeste_dit_tailles_poids_et_noms():
    r = _tabletopia(2, noms=["Gobelin", ""])
    z = zipfile.ZipFile(io.BytesIO(r.content))
    man = json.loads(z.read("tabletopia/manifeste.json").decode("utf-8"))
    assert man["px"] == [750, 1050] and man["dos"] == "commun : un seul fichier de dos"
    assert [c["nom"] for c in man["cartes"]] == ["Gobelin", "Carte 2"]
    import hashlib
    for f in man["fichiers"]:
        assert f["sha256"] == hashlib.sha256(z.read("tabletopia/" + f["nom"])).hexdigest()
        assert f["octets"] <= 2 * 1024 * 1024 and f["px"] == [750, 1050]
    assert "2000" in man["note"] and "séparés" in man["note"]


def test_tabletopia_des_versos_differents_un_fichier_par_carte():
    r = _tabletopia(3, backs="uniques")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    versos = sorted(n for n in z.namelist() if "_verso" in n)
    assert versos == [f"tabletopia/banc-tabletopia_0{i}_verso.jpg" for i in (1, 2, 3)], versos
    assert not any(n.endswith("_dos.jpg") for n in z.namelist())
    v3 = Image.open(io.BytesIO(z.read(versos[2]))).convert("RGB").getpixel((375, 525))
    assert abs(v3[1] - 90) <= 4, v3


def test_tabletopia_sans_verso_aucun_fichier_de_dos_et_c_est_dit():
    r = _tabletopia(2, backs=None)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert not any("dos" in n or "verso" in n for n in z.namelist() if n.endswith(".jpg"))
    assert "aucun verso" in json.loads(z.read("tabletopia/manifeste.json"))["dos"]


def test_tabletopia_a_600_dpi_le_cote_long_est_ramene_a_2000():
    r = _tabletopia(1, dpi=600, backs=None)
    assert r.status_code == 200, r.text
    z = zipfile.ZipFile(io.BytesIO(r.content))
    im = Image.open(io.BytesIO(z.read("tabletopia/banc-tabletopia_01_recto.jpg")))
    # coupe 1500 x 2100 à 600 DPI -> 2100 > 2000 : réduite, proportions gardées (1429 x 2000)
    assert im.size == (1429, 2000), im.size


def test_tabletopia_refuse_ce_qui_ne_vient_pas_du_moteur():
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Mauvais"})
            did = r.json()["deck"]["id"]
            await c.patch(f"/api/cards/{did}", json={"format": {"fmt": "poker_us", "dpi": 300}})
            r1 = await c.post(f"/api/cards/{did}/edition/tabletopia", data={"spec": "{}"},
                              files=[("fronts", ("f.png", _carte(822, 1122, (1, 2, 3)), "image/png"))])
            r2 = await c.post(f"/api/cards/{did}/edition/tabletopia", data={"spec": "{}"})
            return r1, r2
    r1, r2 = asyncio.run(go())
    assert r1.status_code == 400 and "822" in r1.text and "825" in r1.text, r1.text
    assert r2.status_code == 400 and "Aucune carte" in r2.text, r2.text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
