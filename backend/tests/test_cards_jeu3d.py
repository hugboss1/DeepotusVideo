# -*- coding: utf-8 -*-
"""Card Forge — tâche #87 PR B (plan-cartes T16-T17, 04/10/2026) : objets du jeu (jetons, pions, présentoir) et
boîte dépliée en PDF.

DÉCISIONS DE L'UTILISATEUR (04/10) : route HORS du graphe vers print3d ; jeton en RELIEF de la carte ; présentoir qui
TIENT la carte ; VRAIE tuck box (languette, rabats anti-poussière, couvercles à rabat).
Écarts au plan corrigés : base print3d réelle = outputs_path.parent/print3d (sinon l'écran Imprimante ne voit rien) ;
étanchéité « garantie »/« inconnue » (pas « fermee ») ; présentoir du plan = deux plaques sans fond ; patron du plan =
un rectangle plié qui ne ferme pas ; `text_paths` rend des polylignes (le plan les joignait comme des octets) ;
MediaBox en mm2pt (A4 = 595.28 pt), pas px2pt ; `_deck`/`Body` absents de forge3d.
Les objets sont écrits dans un dossier de données TEMPORAIRE ; aucun appel réseau.
Témoin positif : la base (21e9efcd) n'a ni /jeu ni /boite.
Run : cd backend ; & $PY tests/test_cards_jeu3d.py
"""
import asyncio
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp(prefix="cfjeu_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
           "HEYGEN_API_KEY", "FIGMA_TOKEN", "OLLAMA_MODEL", "FAL_KEY"):
    os.environ[_k] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

import pytest                                                    # noqa: E402
from httpx import ASGITransport, AsyncClient                     # noqa: E402

from app.services import print3d as P3                           # noqa: E402
from app.services.cards import forge3d_jeu as J                  # noqa: E402

RACINE = _ICI.parent.parent
BASE = "21e9efcd"


def _png(w=64, h=48):
    from PIL import Image
    im = Image.new("RGB", (w, h), (0, 0, 0))
    for x in range(w // 2):
        for y in range(h):
            im.putpixel((x, y), (255, 255, 255))            # moitié gauche blanche : elle doit MONTER
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def _deck(c, patch=None):
    async def go():
        r = await c.post("/api/cards/decks", json={"name": "Jeu"})
        did = r.json()["deck"]["id"]
        if patch:
            await c.patch(f"/api/cards/{did}", json=patch)
        return did
    return go()


def _run(fn):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            return await fn(c)
    return asyncio.run(go())


def test_temoin_la_base_n_a_ni_jeu_ni_boite():
    d = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/forge3d.py"], capture_output=True,
                       cwd=str(RACINE)).stdout
    assert d and b'"/jeu"' not in d and b'"/boite"' not in d


def test_un_jeton_a_ses_cotes_et_il_est_ferme_et_pose():
    t = J.jeton(25.0, 3.0, 64)
    (x0, x1), (y0, y1), (z0, z1) = P3.bbox(t)
    assert abs((x1 - x0) - 25.0) < 0.05 and abs((y1 - y0) - 25.0) < 0.05 and abs(z1 - z0 - 3.0) < 1e-9 and abs(z0) < 1e-12
    assert len(t) == 4 * 64 and J.fermeture(t) == 0


def test_fermeture_compte_une_arete_ouverte():
    t = J.jeton(20.0, 2.0, 16)
    assert J.fermeture(t[1:]) > 0                       # un triangle retiré : le solide est ouvert, et le compteur le voit


def test_le_pion_s_affine_vers_le_haut_et_tient_debout():
    t = J.pion(22.0, 16.0, 3.0, 3, 32)
    (x0, x1), _y, (z0, z1) = P3.bbox(t)
    assert abs((x1 - x0) - 22.0) < 0.05 and abs(z1 - 9.0) < 1e-9 and abs(z0) < 1e-12 and J.fermeture(t) == 0
    haut = [v for tri in t for v in tri if v[2] > 8.99]
    assert max(abs(v[0]) for v in haut) <= 8.0 + 1e-9                         # la tête : 16 mm de diamètre
    with pytest.raises(ValueError) as e:
        J.pion(16.0, 22.0)
    assert "basculerait" in str(e.value)


def test_le_presentoir_a_un_socle_et_une_rainure_entre_deux_rails():
    t = J.presentoir(74.0, 30.0, 3.0, 1.0, 6.0, 8.0)
    assert J.fermeture(t) == 0
    (x0, x1), (y0, y1), (z0, z1) = P3.bbox(t)
    assert (x1 - x0, y1 - y0, z1) == (74.0, 30.0, 11.0) and z0 == 0.0
    # la rainure : entre y = 14.5 et 15.5, aucun sommet au-dessus du socle
    hauts = [v for tri in t for v in tri if v[2] > 3.0 + 1e-9]
    assert not [v for v in hauts if 14.5 + 1e-9 < v[1] < 15.5 - 1e-9]
    assert {round(v[1], 3) for v in hauts} == {8.5, 11.5, 14.5, 15.5, 18.5, 21.5}     # bords et centres des rails
    sommets = {(round(v[1], 3), round(v[2], 3)) for tri in t for v in tri}
    assert {(8.5, 3.0), (8.5, 11.0), (21.5, 3.0), (21.5, 11.0)} <= sommets and (8.5, 0.0) not in sommets, sorted(sommets)
    with pytest.raises(ValueError):
        J.presentoir(74.0, 15.0, 3.0, 4.0, 6.0, 8.0)              # 6 + 4 + 6 > 15


def test_le_jeton_en_relief_monte_ou_l_image_est_claire():
    from PIL import Image
    t = J.jeton_relief(Image.open(io.BytesIO(_png())), 30.0, 2.0, 1.0, 48)
    assert J.fermeture(t) == 0
    (x0, x1), _y, (z0, z1) = P3.bbox(t)
    assert abs((x1 - x0) - 30.0) < 0.1 and abs(z0) < 1e-12 and abs(z1 - (2.0 + 0.1 + 1.0)) < 1e-6
    hauts = [v for tri in t for v in tri if v[2] > 2.0 + 0.1 + 0.5]
    assert hauts and all(v[0] <= 0.5 for v in hauts)               # le blanc était à GAUCHE : le relief y monte
    rel = [v for tri in t for v in tri if v[2] > 2.0 + 1e-9]
    assert max((v[0] ** 2 + v[1] ** 2) ** 0.5 for v in rel) <= 15.0, "le relief reste DANS le disque"
    with pytest.raises(ValueError):
        J.jeton_relief(Image.new("L", (4, 4)), 30.0)
    # une image large dont seul le TIERS GAUCHE est blanc : le carré central est noir, le relief reste plat
    im = Image.new("L", (96, 32), 0)
    im.paste(255, (0, 0, 32, 32))
    t2 = J.jeton_relief(im, 30.0, 2.0, 1.0, 48)
    assert max(v[2] for tri in t2 for v in tri) < 2.0 + 0.1 + 0.05, "le relief vient du carré CENTRAL"


@pytest.mark.parametrize("mauvais", [(0.0, 3.0), (400.0, 3.0), (25.0, 0.0), (25.0, 60.0), ("x", 3.0)])
def test_les_bornes_sont_dites_en_mm(mauvais):
    with pytest.raises(ValueError) as e:
        J.jeton(mauvais[0], mauvais[1], 32)
    assert "mm" in str(e.value)


def test_la_route_jeu_ecrit_dans_le_dossier_de_l_imprimante_et_le_stl_se_relit():
    async def fn(c):
        did = await _deck(c)
        r = await c.post(f"/api/cards/{did}/forge3d/jeu", data={"objet": "jeton", "params": json.dumps({"diam_mm": 25, "ep_mm": 3, "cotes": 48}),
                                                                 "nom": "jeton mana"})
        return did, r
    did, r = _run(fn)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["triangles"] == 4 * 48 and j["objet"] == "jeton"
    from app.config import settings
    base = settings.outputs_path.parent / "print3d"
    p = base / j["dossier"] / j["stl"]
    assert p.is_file(), p
    relu = P3.lire_stl(p.read_bytes())
    (x0, x1), _y, (z0, z1) = P3.bbox(relu)
    assert abs((x1 - x0) - 25.0) < 0.05 and abs((z1 - z0) - 3.0) < 1e-4
    meta = json.loads((base / j["dossier"] / "impression.json").read_text(encoding="utf-8"))
    assert meta["etancheite"] == "garantie" and meta["source"] == f"cardforge/{did}/jeton"
    assert any(e.get("dossier") == j["dossier"] for e in P3.lister_exports(base))      # l'écran Imprimante le voit


def test_le_presentoir_prend_la_carte_et_l_epaisseur_du_deck():
    async def fn(c):
        did = await _deck(c, {"solid": {"thickness_mm": 0.5}})
        return await c.post(f"/api/cards/{did}/forge3d/jeu", data={"objet": "presentoir"})
    r = _run(fn)
    assert r.status_code == 200, r.text
    p = r.json()["params"]
    assert p["largeur_mm"] == 73.0 and p["rainure_mm"] == 1.1, p        # format par défaut 63 mm + 10 ; carte 0,5 + 0,6


def test_le_jeton_en_relief_par_la_route_et_ses_refus():
    async def fn(c):
        did = await _deck(c)
        ok = await c.post(f"/api/cards/{did}/forge3d/jeu", data={"objet": "jeton_relief", "params": json.dumps({"grille": 48})},
                          files={"image": ("carte.png", _png(), "image/png")})
        sans = await c.post(f"/api/cards/{did}/forge3d/jeu", data={"objet": "jeton_relief"})
        jpeg = await c.post(f"/api/cards/{did}/forge3d/jeu", data={"objet": "jeton_relief"},
                            files={"image": ("x.png", b"pas une image", "image/png")})
        inconnu = await c.post(f"/api/cards/{did}/forge3d/jeu", data={"objet": "dragon"})
        borne = await c.post(f"/api/cards/{did}/forge3d/jeu", data={"objet": "jeton", "params": json.dumps({"diam_mm": 0})})
        mal = await c.post(f"/api/cards/{did}/forge3d/jeu", data={"objet": "jeton", "params": "[1]"})
        deck = await c.post("/api/cards/deck_zzzzzzzz/forge3d/jeu", data={"objet": "jeton"})
        return ok, sans, jpeg, inconnu, borne, mal, deck
    ok, sans, jpeg, inconnu, borne, mal, deck = _run(fn)
    assert ok.status_code == 200 and ok.json()["triangles"] > 1000, ok.text
    assert sans.status_code == 400 and "image" in sans.text
    assert jpeg.status_code == 400 and inconnu.status_code == 400 and "dragon" in inconnu.text
    assert borne.status_code == 400 and "mm" in borne.text and mal.status_code == 400
    assert deck.status_code in (400, 404)


def test_le_patron_est_une_vraie_tuck_box_aux_dimensions_du_deck_plus_le_jeu():
    p = J.patron_boite(63.0, 88.0, 20.0, 1.0, 15.0)
    assert p["boite_mm"] == [64.0, 89.0, 21.0]
    L, H, E = 64.0, 89.0, 21.0
    assert p["developpe_mm"] == [round(2 * L + 2 * E + 10.0, 3), round(H + 2 * E + 30.0, 3)]
    c = p["contour"]
    assert c[0] == c[-1], "le contour se referme"
    xs, ys = [q[0] for q in c], [q[1] for q in c]
    assert max(xs) == 2 * L + 2 * E + 10.0 and max(ys) == H + 2 * E + 30.0 and min(xs) == 0.0 and min(ys) == 0.0
    # les quatre arêtes verticales du corps, les charnières et les rabats : 12 plis
    assert len(p["plis"]) == 12 and [s[0] for s in p["plis"][:4]] == [L, L + E, 2 * L + E, 2 * L + 2 * E]
    # l'encoche du pouce : le contour descend SOUS le haut du corps, au milieu de la face
    y1 = 15.0 + E + H
    assert min(q[1] for q in c if L + E < q[0] < 2 * L + E) < y1 - 5.0


def test_la_boite_trop_grande_propose_la_feuille_qui_conviendrait_ou_le_paysage():
    with pytest.raises(ValueError) as e:
        J.patron_boite(88.0, 126.0, 25.0, 1.0, 15.0)          # tarot : 2*89+2*26+10 = 240 mm ; tient en A3
    assert "A4" in str(e.value) and "A3" in str(e.value) and "mm" in str(e.value)
    p = J.patron_boite(63.0, 88.0, 34.0, 1.0, 15.0)            # 2x64 + 2x35 + 10 = 208 (+12) : A4 en PAYSAGE seulement
    assert p["paysage"] is True
    with pytest.raises(ValueError) as e:
        J.patron_boite(63.0, 88.0, 140.0, 1.0, 15.0, feuille="a3")
    assert "aucune feuille" in str(e.value)
    with pytest.raises(ValueError):
        J.patron_boite(63.0, 88.0, 20.0, feuille="tabloid")


def test_l_epaisseur_vient_de_la_piece_05():
    from app.services.cards import contract as CT
    assert abs(J.epaisseur_deck_mm(60, CT.THICKNESS_MM_DEFAULT) - 60 * 0.32) < 1e-9


def test_le_pdf_de_la_boite_coupe_en_plein_plie_en_pointilles_et_le_dit():
    async def fn(c):
        did = await _deck(c, {"format": {"fmt": "poker_eu", "dpi": 300}})
        ok = await c.post(f"/api/cards/{did}/forge3d/boite", json={"cartes": 60, "feuille": "a4"})
        trop = await c.post(f"/api/cards/{did}/forge3d/boite", json={"cartes": 400, "feuille": "a4"})
        zero = await c.post(f"/api/cards/{did}/forge3d/boite", json={"cartes": 0})
        lettre = await c.post(f"/api/cards/{did}/forge3d/boite", json={"cartes": "abc"})
        pays = await c.post(f"/api/cards/{did}/forge3d/boite", json={"cartes": 100, "feuille": "a4"})
        did2 = await _deck(c, {"format": {"fmt": "poker_eu", "dpi": 300}, "solid": {"thickness_mm": 0.5}})
        epais = await c.post(f"/api/cards/{did2}/forge3d/boite", json={"cartes": 60})
        return ok, trop, zero, lettre, pays, epais
    ok, trop, zero, lettre, pays, epais = _run(fn)
    assert ok.status_code == 200, ok.text
    assert ok.headers["content-type"] == "application/pdf"
    from pypdf import PdfReader
    rd = PdfReader(io.BytesIO(ok.content))
    assert len(rd.pages) == 1
    box = [round(float(v), 2) for v in rd.pages[0].mediabox]
    assert box == [0.0, 0.0, 595.28, 841.89], box                # A4 nominal, en points
    flux = rd.pages[0].get_contents().get_data()
    assert b"[] 0 d" in flux and b"] 0 d" in flux.replace(b"[] 0 d", b"")      # plein, puis pointillés
    pointilles = flux.split(b"] 0 d")[2].split(b"[] 0 d")[0]
    assert pointilles.count(b" l S") == 12, pointilles.count(b" l S")
    assert b" h S" in flux                                        # le contour, fermé
    # poker_eu 63 x 88 ; 60 cartes de 0,32 = 19,2 mm ; jeu 1 mm
    assert ok.headers["X-CF-Boite-Mm"] == "64x89x20.2" and ok.headers["X-CF-Cartes"] == "60", dict(ok.headers)
    assert ok.headers["X-CF-Feuille"] == "a4" and ok.headers["X-CF-Jeu-Mm"] == "1"
    assert trop.status_code == 400 and "aucune feuille" in trop.text
    assert zero.status_code == 400 and "entre 1 et 1000" in zero.text and lettre.status_code == 400
    # 100 cartes : 2x64 + 2x33 + 10 = 204 mm (+12) ne tient qu'en PAYSAGE
    assert pays.status_code == 200 and pays.headers["X-CF-Feuille"] == "a4-paysage", pays.text
    assert [round(float(v), 2) for v in PdfReader(io.BytesIO(pays.content)).pages[0].mediabox] == [0.0, 0.0, 841.89, 595.28]
    # l'épaisseur vient de la pièce 05 : 60 x 0,5 + 1
    assert epais.headers["X-CF-Boite-Mm"] == "64x89x31", dict(epais.headers)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
