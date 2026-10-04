# -*- coding: utf-8 -*-
"""Card Forge — tâche #87 PR C (plan-cartes T18-T19, 04/10/2026) : livret de règles en PDF, mockup, fiche produit.

DÉCISION DE L'UTILISATEUR (04/10) : mockup en éventail 2D (aucun moteur 3D dans la pièce 11).
Écarts au plan corrigés : `settings.fonts_path` n'existe pas (fonte par défaut de PIL partout) → type.fonts_dir ;
`Body` absent d'edition.py ; la tournette est dans la pièce 05 (Volume), pas au Forge 3D ; la fiche lit les langues
dans la table au lieu de les recevoir ; pagination à la hauteur réelle des lignes (intertitres « # »).
Témoin positif : la base (21ce8994) n'a ni /livret ni /mockup ni /fiche.
Run : cd backend ; & $PY tests/test_cards_livret.py
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

_tmp = tempfile.mkdtemp(prefix="cflivret_")
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
from PIL import Image                                            # noqa: E402

from app.services.cards import edition_livret as L               # noqa: E402

RACINE = _ICI.parent.parent
BASE = "21ce8994"


def _png(w=825, h=1125, rgb=(200, 30, 30)):
    b = io.BytesIO()
    Image.new("RGB", (w, h), rgb).save(b, "PNG")
    return b.getvalue()


def _run(fn):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Règles"})
            return await fn(c, r.json()["deck"]["id"])
    return asyncio.run(go())


def test_temoin_la_base_n_a_ni_livret_ni_mockup_ni_fiche():
    d = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/edition.py"], capture_output=True,
                       cwd=str(RACINE)).stdout
    assert d and b'"/livret"' not in d and b'"/mockup"' not in d and b'"/fiche"' not in d


def test_la_fonte_vient_des_fontes_servies_et_non_du_defaut_de_pil():
    assert "Inter.ttf" in L.polices() and "PolandKaito.otf" in L.polices()      # l'extension n'est pas devinée
    assert L.police("", 40).getname()[0] == "Inter"
    assert L.police("Cinzel.ttf", 40).getname()[0] == "Cinzel"
    assert L.police("..\\..\\secret.ttf", 40).getname()[0] == "Inter"           # un chemin ne sort pas du dossier
    arial = pathlib.Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts" / "arial.ttf"
    if arial.is_file():
        assert L.police(str(arial), 40).getname()[0] == "Inter", "une fonte HORS du dossier servi ne se charge pas"


def test_sans_fonte_servie_le_corps_demande_est_tenu(monkeypatch, tmp_path):
    from app.services.cards import type as TY
    monkeypatch.setattr(TY, "fonts_dir", lambda: tmp_path)
    assert L.police("", 40).size == 40 and L.polices() == []


def test_la_pagination_coupe_sans_rien_perdre_et_compte_les_intertitres():
    txt = "\n\n".join("# Partie %d\nParagraphe %d. %s" % (i, i, "mot " * 60) for i in range(20))
    P = L.paginer(txt, "a5", 38)
    assert len(P["pages"]) >= 3
    rendu = " ".join(t for p in P["pages"] for _g, t in p)
    assert rendu.count("Paragraphe 0.") == 1 and rendu.count("Paragraphe 19.") == 1 and rendu.count("mot") == 20 * 60
    titres = [t for p in P["pages"] for g, t in p if g == "titre"]
    assert titres[0] == "Partie 0" and len(titres) == 20
    assert all(p and p[0][0] != "blanc" for p in P["pages"])              # aucun blanc en tête de page
    # chaque page tient dans la hauteur utile
    for i, p in enumerate(P["pages"]):
        h = sum(P["haut"][g] for g, _t in p)
        assert h <= P["h"] - 2 * P["marge"] - 2 * 38, (i, h)


def test_un_mot_plus_long_que_la_ligne_est_coupe_et_non_perdu():
    P = L.paginer("A" * 3000, "a5", 60)
    joint = "".join(t for p in P["pages"] for _g, t in p)
    assert joint.count("A") == 3000 and max(len(t) for p in P["pages"] for _g, t in p) < 3000
    pleines = [t for p in P["pages"] for _g, t in p][:-1]
    assert min(len(t) for t in pleines) > 20, "chaque morceau remplit sa ligne (le plus long préfixe qui tient)"


def test_jamais_de_blanc_en_tete_de_page():
    for texte, cap in (("ligne\n\n\n" * 300, 38), ("ligne\n\n" * 300, 52), ("ligne\n\n\n\n" * 300, 45)):
        P = L.paginer(texte, "a5", cap)          # ces trois-là coupent SUR un blanc sans la garde (mesuré)
        assert len(P["pages"]) > 3 and all(p[0][0] != "blanc" for p in P["pages"]), cap


def test_les_bornes_du_livret_sont_dites():
    for args, mot in ((("x", "a3"), "Feuille"), (("x", "a5", 5), "entre 20 et 90"), (("x" * 200_001,), "trop long")):
        with pytest.raises(ValueError) as e:
            L.paginer(*args)
        assert mot in str(e.value)


def test_le_livret_est_un_pdf_a5_a_300_dpi_avec_sa_planche_et_l_ecart_dit():
    async def fn(c, did):
        files = [("images", (f"c{i}.png", _png(), "image/png")) for i in range(7)]
        ok = await c.post(f"/api/cards/{did}/edition/livret", data={"spec": json.dumps({
            "titre": "Règles du jeu", "texte": "# But du jeu\n\n" + "mot " * 1500, "feuille": "a5"})}, files=files)
        nu = await c.post(f"/api/cards/{did}/edition/livret", data={"spec": json.dumps({"texte": "Court."})})
        mauvais = await c.post(f"/api/cards/{did}/edition/livret", data={"spec": "[1]"})
        image = await c.post(f"/api/cards/{did}/edition/livret", data={"spec": "{}"},
                             files=[("images", ("x.png", b"rien", "image/png"))])
        feuille = await c.post(f"/api/cards/{did}/edition/livret", data={"spec": json.dumps({"feuille": "a0"})})
        corps = await c.post(f"/api/cards/{did}/edition/livret", data={"spec": json.dumps({"cap_px": "gros"})})
        return ok, nu, mauvais, image, feuille, corps
    ok, nu, mauvais, image, feuille, corps = _run(fn)
    assert ok.status_code == 200, ok.text
    from pypdf import PdfReader
    rd = PdfReader(io.BytesIO(ok.content))
    box = [round(float(v), 2) for v in rd.pages[0].mediabox]
    assert box == [0.0, 0.0, 419.52, 595.2], box                     # A5 à 300 DPI : 1748 x 2480 px
    assert int(ok.headers["X-CF-Pages"]) == len(rd.pages) and int(ok.headers["X-CF-Pages-Texte"]) >= 2
    assert int(ok.headers["X-CF-Pages"]) == int(ok.headers["X-CF-Pages-Texte"]) + 1      # 7 cartes : une planche
    assert ok.headers["X-CF-Images"] == "7" and ok.headers["X-CF-Texte"] == "raster"
    assert nu.status_code == 200 and nu.headers["X-CF-Pages"] == "1"
    assert mauvais.status_code == 400 and image.status_code == 400 and "illisible" in image.text
    assert feuille.status_code == 400 and "Feuille" in feuille.text and corps.status_code == 400


def test_la_planche_garde_les_proportions_et_change_de_page():
    pl = L._planches([Image.new("RGB", (825, 1125), (0, 0, 255))] * 13, 1748, 2480, 177)
    assert len(pl) == 2                                               # 3 colonnes x 4 rangées = 12 par page
    px = pl[0].getpixel((177 + 5, 177 + 5))
    assert px == (0, 0, 255) and pl[1].getpixel((177 + 5, 177 + 5)) == (0, 0, 255)
    gap = round(3.0 / 25.4 * 300)
    cw = (1748 - 2 * 177 - 2 * gap) // 3
    ch = int(cw * 1125 / 825)                                         # la proportion de la CARTE, pas un carré
    assert pl[0].getpixel((182, 177 + ch - 3)) == (0, 0, 255) and pl[0].getpixel((182, 177 + ch + gap // 2)) == (255, 255, 255)
    with pytest.raises(ValueError):
        L.build_livret("t", "x", [Image.new("RGB", (8, 8))] * (L.IMAGES_MAX + 1))


def test_le_mockup_aux_formats_des_reseaux_et_cinq_cartes_au_plus():
    for cible, att in (("carre", (1080, 1080)), ("story", (1080, 1920)), ("paysage", (1600, 900))):
        im = L.mockup([Image.new("RGB", (825, 1125), (10, 20, 30))], cible, "Deepotus", "60 cartes")
        assert im.size == att, (cible, im.size)
    (w, h), plan = L.mockup_plan([(825, 1125)] * 7, "paysage")
    assert len(plan) == 5 and [round(p["rot"]) for p in plan] == [12, 6, 0, -6, -12]
    assert min(p["x"] for p in plan) >= 0 and max(p["x"] + p["w"] for p in plan) <= w * 0.9 + 1
    assert all(p["h"] <= h * 0.62 + 1 for p in plan)
    (w, h), plan = L.mockup_plan([(825, 1125)] * 5, "story")      # étroit : l'éventail est RÉDUIT pour tenir
    assert min(p["x"] for p in plan) >= 0 and max(p["x"] + p["w"] for p in plan) <= w * 0.9 + 1, plan
    with pytest.raises(ValueError):
        L.mockup_plan([(825, 1125)], "tiktok")
    with pytest.raises(ValueError):
        L.mockup_plan([], "carre")


def test_le_mockup_pose_les_cartes_sur_le_fond_choisi():
    im = L.mockup([Image.new("RGB", (825, 1125), (255, 0, 0))], "carre", "", "", "#00ff00")
    assert im.getpixel((5, 5)) == (0, 255, 0) and im.getpixel((540, 560)) == (255, 0, 0)
    assert L.mockup([Image.new("RGB", (8, 8))], "carre", fond="zz").getpixel((2, 2)) == (14, 18, 24)


def test_la_carte_est_montree_a_la_coupe_et_aux_coins_arrondis():
    im = Image.new("RGB", (825, 1125), (255, 0, 0))
    im.paste((0, 0, 255), (38, 38, 38 + 750, 38 + 1050))
    c = L.a_la_coupe(im, (38, 38, 788, 1088), 35.4)
    assert c.size == (750, 1050) and c.getpixel((375, 525)) == (0, 0, 255, 255)
    assert c.getpixel((0, 0))[3] == 0 and c.getpixel((749, 1049))[3] == 0 and c.getpixel((375, 0))[3] == 255

    async def fn(c, did):
        await c.patch(f"/api/cards/{did}", json={"format": {"fmt": "poker_us", "dpi": 300}})
        b = io.BytesIO()
        im.save(b, "PNG")
        return await c.post(f"/api/cards/{did}/edition/mockup", data={"spec": '{"cible":"carre","fond":"#00ff00","titre":""}'},
                            files=[("images", ("c.png", b.getvalue(), "image/png"))])
    r = _run(fn)
    assert r.status_code == 200, r.text
    out = Image.open(io.BytesIO(r.content)).convert("RGB")
    rouges = sum(1 for p in out.getdata() if p[0] > 200 and p[1] < 60 and p[2] < 60)
    assert rouges == 0, f"{rouges} pixels du fond perdu dans le mockup"
    assert out.getpixel((540, 560))[2] > 200


def test_la_route_mockup_rend_un_png_et_refuse_six_cartes():
    async def fn(c, did):
        ok = await c.post(f"/api/cards/{did}/edition/mockup", data={"spec": '{"cible":"story"}'},
                          files=[("images", ("c.png", _png(), "image/png"))])
        six = await c.post(f"/api/cards/{did}/edition/mockup", data={"spec": "{}"},
                           files=[("images", (f"c{i}.png", _png(), "image/png")) for i in range(6)])
        rien = await c.post(f"/api/cards/{did}/edition/mockup", data={"spec": "{}"})
        cible = await c.post(f"/api/cards/{did}/edition/mockup", data={"spec": '{"cible":"tiktok"}'},
                             files=[("images", ("c.png", _png(), "image/png"))])
        return ok, six, rien, cible
    ok, six, rien, cible = _run(fn)
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/png" and ok.headers["X-CF-Px"] == "1080x1920"
    assert Image.open(io.BytesIO(ok.content)).size == (1080, 1920) and ok.headers["X-CF-Cartes-Montrees"] == "1"
    assert six.status_code == 400 and "5 au plus" in six.text
    assert rien.status_code == 400 and cible.status_code == 400 and "tiktok" in cible.text


def test_la_fiche_dit_les_chiffres_et_lit_les_langues_dans_la_table():
    async def fn(c, did):
        await c.patch(f"/api/cards/{did}", json={"format": {"fmt": "poker_us", "dpi": 300}, "solid": {"thickness_mm": 0.30},
                                                 "data": {"columns": ["id", "nom_fr", "nom_en", "qty"], "rows": []}})
        ok = await c.post(f"/api/cards/{did}/edition/fiche", json={"cartes": 60})
        zero = await c.post(f"/api/cards/{did}/edition/fiche", json={"cartes": 0})
        texte = await c.post(f"/api/cards/{did}/edition/fiche", json={"cartes": "beaucoup"})
        return ok, zero, texte
    ok, zero, texte = _run(fn)
    assert ok.status_code == 200, ok.text
    f = ok.json()
    assert f["cartes"] == 60 and f["format"] == "Poker US 2,5 x 3,5 in" and f["dimensions_mm"] == [63.5, 88.9]
    assert f["epaisseur_deck_mm"] == 18.0 and f["epaisseur_carte_mm"] == 0.3
    assert f["boite_mm"] == [64.5, 89.9, 19.0], f["boite_mm"]                 # le patron de la boîte dépliée
    assert f["langues"] == ["français", "anglais"]
    assert "60 cartes au format Poker US" in f["texte"] and "63,5 × 88,9 mm" in f["texte"] and "français, anglais" in f["texte"]
    assert zero.status_code == 400 and texte.status_code == 400


def test_sans_colonne_de_langue_la_fiche_ne_les_invente_pas():
    f = L.fiche({"format": {"fmt": "poker_eu"}, "data": {"columns": ["nom", "pv"]}}, 10, 0.32)
    assert f["langues"] == [] and "Langues" not in f["texte"]


def test_les_polices_sont_servies_par_la_piece():
    async def fn(c, did):
        return await c.get(f"/api/cards/{did}/edition/polices")
    r = _run(fn)
    j = r.json()
    assert r.status_code == 200 and "Inter.ttf" in j["polices"] and j["defaut"] == "Inter.ttf" and j["mockup_max"] == 5


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
