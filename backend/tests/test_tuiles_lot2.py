# -*- coding: utf-8 -*-
"""Tuiles — lot 2 (plan 2026-09-03-plan-tuiles, tâche t116 : T10-T12).
T10 (D1) : une matière du Material Forge devient un jeu de tuiles — sa couleur de base (`basecolor.png`, celle que le
Forge affiche : `bake_levels` ne touche que métal/rugosité/ORM), désignée par son id `mat_xxxxxxxx`. La source est
ENREGISTRÉE TELLE QUE REÇUE dans le meta (le plan l'oubliait : `/apercu` et `/mesures` rejouent le jeu depuis le meta
et seraient tombés en 400), et les gardes de l'image (antislash, image illisible → 400) restent.
Run: python tests/test_tuiles_lot2.py   (depuis backend/)"""
import asyncio
import os
import pathlib
import random
import re
import sys
import tempfile
import traceback

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = tempfile.mkdtemp(prefix="dztuiles2_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["FAL_KEY"] = ""; os.environ["ELEVENLABS_API_KEY"] = ""; os.environ["HEYGEN_API_KEY"] = ""
pathlib.Path(_tmp, "images").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger                                # noqa: E402
logger.remove()
from PIL import Image                                    # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend" / "tilelab"


def _bruit(s=64, seed=1, teinte=(0, 0, 0)):
    rng = random.Random(seed)
    im = Image.frombytes("RGB", (s, s), bytes(rng.randrange(200) for _ in range(s * s * 3)))
    return Image.eval(im, lambda v: v).point(lambda v: v) if not any(teinte) else \
        Image.merge("RGB", [b.point(lambda v, t=t: min(255, v + t)) for b, t in zip(im.split(), teinte)])


def _matiere(nom, img, avec_basecolor=True):
    """Une vraie matière du Forge : meta.json écrit par create_material, cartes par save_maps."""
    from app.services import material_store as MS
    m = MS.create_material(name=nom, prompt=nom)
    if avec_basecolor:
        MS.save_maps(m["id"], {"basecolor": img})
    else:
        MS.save_maps(m["id"], {"roughness": img.convert("L")})
    return m["id"]


def _image(nom, img):
    from app.config import settings
    img.save(settings.images_path / nom, "PNG")
    return nom


def _client():
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


# ═════════════════════════════════ T10 (D1) ══════════════════════════════════

def test_une_matiere_du_forge_devient_un_jeu_et_se_rejoue():
    mid_a = _matiere("herbe", _bruit(64, 1, (0, 40, 0)))
    b = _image("t10_terre.png", _bruit(64, 2, (40, 20, 0)))

    async def sc():
        async with _client() as c:
            r = await c.post("/api/tiles/jeu", json={"matiere_a": {"materiau": mid_a}, "matiere_b": {"image": b},
                                                     "jeu": "blob16", "cote": 32})
            assert r.status_code == 200, r.text
            tid = r.json()["tid"]
            meta = (await c.get(f"/api/tiles/{tid}")).json()
            assert meta["source_a"] == {"materiau": mid_a}, meta["source_a"]   # telle que reçue
            assert meta["source_b"] == {"image": b}, meta["source_b"]
            # le jeu se REJOUE depuis le meta : l'aperçu et les mesures marchent sur une matière du Forge
            ap = await c.post(f"/api/tiles/{tid}/apercu", json={"cases": 4, "densite": 0.5, "graine": 3})
            assert ap.status_code == 200, ap.text
            me = await c.post(f"/api/tiles/{tid}/mesures", json={"cases": 4, "densite": 0.5, "graine": 3})
            assert me.status_code == 200, me.text
            # une forme aussi
            r = await c.post("/api/tiles/jeu", json={"matiere_a": {"materiau": mid_a}, "forme": "iso", "cote": 32})
            assert r.status_code == 200, r.text
            assert (await c.get(f"/api/tiles/{r.json()['tid']}")).json()["source_a"] == {"materiau": mid_a}
    asyncio.run(sc())


def test_la_matiere_donne_SA_couleur_de_base():
    from app.services import tiles_api as TA
    img = _bruit(48, 9, (60, 0, 0))
    mid = _matiere("rouille", img)
    lu = TA._charger_matiere({"materiau": mid}, "matiere_a")
    assert lu.size == (48, 48) and lu.tobytes() == img.convert("RGB").tobytes()


def test_les_refus_d_une_matiere():
    from fastapi import HTTPException
    from app.services import tiles_api as TA
    sans = _matiere("sans couleur", _bruit(32, 4), avec_basecolor=False)
    img = _image("t10_ok.png", _bruit(32, 5))
    cas = [({"materiau": "mat_00000000"}, "introuvable"), ({"materiau": "../mat_x"}, "matiere"),
           ({"materiau": sans}, "couleur"), ({"materiau": sans, "image": img}, "une seule"),
           ({}, "image"), ("x", "objet"),
           ({"image": "..\\dehors.png"}, "introuvable")]                       # la garde de l'antislash reste
    for spec, mot in cas:
        try:
            TA._charger_matiere(spec, "matiere_a")
            raise AssertionError(f"accepté : {spec}")
        except HTTPException as e:
            assert e.status_code == 400 and mot in str(e.detail).lower(), (spec, e.detail)
    from app.config import settings
    (settings.images_path / "t10_casse.png").write_bytes(b"pas une image")
    try:
        TA._charger_matiere({"image": "t10_casse.png"}, "matiere_a")
        raise AssertionError("image illisible acceptée")
    except HTTPException as e:
        assert e.status_code == 400 and "illisible" in e.detail, e.detail


def test_ecran_le_jeu_et_les_formes_prennent_aussi_une_matiere_du_forge():
    html = (FRONT / "index.html").read_text(encoding="utf-8")
    js = (FRONT / "jeu.js").read_text(encoding="utf-8")
    for ident in ("jeuSrcLib", "jeuSrcForge", "formeSrcLib", "formeSrcForge"):
        assert html.count(f'id="{ident}"') == 1, ident
    assert '"/materials"' in js, "la liste des matières vient du Forge"
    assert 'm.maps || []).includes("basecolor")' in js, "seules les matières qui ONT une couleur de base"
    assert "/map/basecolor.png" in js, "la vignette d'une matière = sa couleur de base"
    # une seule fonction fabrique le corps envoyé : image OU materiau, jamais les deux
    assert "function specDe(" in js and "{ materiau: s.id }" in js and "{ image: s.id }" in js
    assert "matiere_a: specDe(etat.a), matiere_b: specDe(etat.b)" in js
    assert "matiere_a: specDe(etat.matiere)" in js


# ═════════════════════════════════ T11 (D2) ══════════════════════════════════
# La route RÉPOND un prompt contraint par la planche et la palette d'un LIEU de la bible : elle ne génère rien, le
# banc ne paie rien. ÉCART AU PLAN : sa planche de banc était UNIE — `_palette_colors` rend les couleurs DISTINCTES
# trouvées (Pillow 12 : 1 couleur), et l'assertion « 6 couleurs » échouait ; la planche est ici en six bandes.

def _planche_six():
    couleurs = [(200, 40, 30), (30, 160, 170), (20, 30, 60), (230, 220, 200), (90, 140, 40), (120, 60, 140)]
    im = Image.new("RGB", (96, 64))
    for i, c in enumerate(couleurs):
        im.paste(Image.new("RGB", (16, 64), c), (16 * i, 0))
    return im


def test_prompt_lieu_porte_la_palette_de_la_planche():
    from app.services.storage import BibleEntity, async_session_factory, init_db

    async def sc():
        await init_db()
        planche = _image("lieu_planche.png", _planche_six())
        async with async_session_factory() as s:
            s.add(BibleEntity(id="lieu-banc", kind="place", name="la crypte turquoise",
                              description="une crypte engloutie", style_notes="pierre humide, lueur cyan",
                              ref_image=planche))
            s.add(BibleEntity(id="perso-banc", kind="character", name="le pilote"))
            s.add(BibleEntity(id="lieu-nu", kind="place", name="le vide"))
            s.add(BibleEntity(id="lieu-casse", kind="place", name="la ruine", ref_image="absente.png"))
            await s.commit()
        async with _client() as c:
            r = await c.post("/api/tiles/prompt-lieu", json={"entity_id": "lieu-banc", "surface": "sol de pierre"})
            assert r.status_code == 200, r.text
            d = r.json()
            assert d["lieu"] == "la crypte turquoise" and d["planche"] == planche, d
            assert 1 <= len(d["palette"]) <= 6 and all(re.fullmatch(r"#[0-9a-f]{6}", x) for x in d["palette"]), d
            # LUES sur la planche, pas inventées : chaque bande a sa couleur dans la palette, à la quantification près
            # (Pillow rend #c12928 pour une bande #c8281e)
            pal = [tuple(int(x[i:i + 2], 16) for i in (1, 3, 5)) for x in d["palette"]]
            for bande in ((200, 40, 30), (30, 160, 170), (20, 30, 60), (230, 220, 200), (90, 140, 40), (120, 60, 140)):
                assert any(max(abs(u - v) for u, v in zip(bande, c)) <= 16 for c in pal), (bande, d["palette"])
            for morceau in ("sol de pierre", "la crypte turquoise", "une crypte engloutie",
                            "pierre humide, lueur cyan", "seamless", "top-down", *d["palette"]):
                assert morceau in d["prompt"], morceau
            assert set(d) == {"entity_id", "lieu", "planche", "palette", "surface", "prompt"}, "un formateur"
            r = await c.post("/api/tiles/prompt-lieu", json={"entity_id": "inconnu"})
            assert r.status_code == 404 and "inconnu" in r.text, r.text
            r = await c.post("/api/tiles/prompt-lieu", json={"entity_id": "perso-banc"})
            assert r.status_code == 400 and "lieu" in r.text.lower(), r.text
            r = await c.post("/api/tiles/prompt-lieu", json={})
            assert r.status_code == 400, r.text
            for eid in ("lieu-nu", "lieu-casse"):           # sans planche lisible : un prompt quand même, sans palette
                r = await c.post("/api/tiles/prompt-lieu", json={"entity_id": eid})
                assert r.status_code == 200 and r.json()["palette"] == [] and r.json()["planche"] == "", r.text
            assert "palette libre" in r.json()["prompt"].lower(), r.json()["prompt"]
            long = await c.post("/api/tiles/prompt-lieu", json={"entity_id": "lieu-nu", "surface": "x" * 500})
            assert len(long.json()["surface"]) == 80, "la surface est bornée"
    asyncio.run(sc())


def test_ecran_offre_le_style_d_un_lieu():
    js = (FRONT / "jeu.js").read_text(encoding="utf-8")
    html = (FRONT / "index.html").read_text(encoding="utf-8")
    assert '"/tiles/prompt-lieu"' in js and '"/bible/entities?kind=place"' in js
    for ident in ("lieuSel", "lieuSurface", "lieuRun", "lieuPrompt", "lieuCopier", "lieuPalette"):
        assert html.count(f'id="{ident}"') == 1, ident
    i = html.index('id="tlJeuSrc"')
    assert i < html.index('id="lieuSel"') < html.index('id="tlFormesSrc"'), "dans la colonne source du mode Jeu"
    assert "/images/generate" not in js, "la route formate, elle ne génère pas : aucun tir payant depuis ici"


def _main():
    rouges = []
    for nom, fn in sorted(globals().items()):
        if nom.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  ✓ {nom}")
            except Exception:                   # noqa: BLE001
                rouges.append(nom); print(f"  ✗ {nom}\n{traceback.format_exc(limit=3)}")
    print(f"\n{'OK' if not rouges else 'ROUGE'} — {len(rouges)} echec(s) (tuiles lot 2)")
    sys.exit(1 if rouges else 0)


if __name__ == "__main__":
    _main()
