"""T110 (plan-sprites T7, P5a) — réordonner / dupliquer / supprimer une feuille FAITE, sans repayer : la feuille EST
relue, et le piège nommé (« _assemble écrit frames/000.png pendant qu'il lit ses entrées ») est couvert par l'ordre
[3, 0, 0], exactement celui qui le déclencherait.

Run: python tests/test_sprite_editor.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzsed_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = ""
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
COULEURS = [(220, 40, 40, 255), (40, 220, 40, 255), (40, 40, 220, 255), (220, 220, 40, 255)]


def _post(job, corps):
    """POST /reassemble par ASGITransport (TestClient bloque à la fermeture sur ce dépôt)."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    async def main():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post(f"/api/assets/sprite/{job}/reassemble", json=corps)
            return r.status_code, r.text
    return asyncio.run(main())


def _png(nom, couleur, taille=(24, 24)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([2, 2, taille[0] - 3, taille[1] - 3], fill=couleur)
    im.save(settings.images_path / nom)
    return nom


def _feuille(job, anim=None):
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"{job}-{i}.png", c) for i, c in enumerate(COULEURS)]
    corps = {"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128}, "columns": 2, "fps_sample": 8}
    if anim:
        corps["anim"] = anim
    asyncio.run(S.generate_sprites(corps, job))
    return settings.outputs_path / "sprites" / job


def _centres(sheet_path, n, cols, cote):
    with Image.open(sheet_path) as sh:
        rgba = sh.convert("RGBA")
        return [rgba.getpixel(((i % cols) * cote + cote // 2, (i // cols) * cote + cote // 2)) for i in range(n)]


def test_reordonner_dupliquer_supprimer_en_un_seul_ordre():
    d = _feuille("j-edit", {"durations": [70, 80, 90, 100]})
    with Image.open(d / "frames" / "003.png") as c3:
        octets3 = c3.convert("RGBA").tobytes()
    st, txt = _post("j-edit", {"order": [3, 0, 0], "columns": 3})
    assert st == 200, txt
    assert json.loads(txt)["frames"] == 3
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert len(m["frames"]) == 3
    assert m["grid"] == {"cols": 3, "rows": 1, "cell_w": 128, "cell_h": 128}
    assert m["source"]["reassembled"] is True and m["source"]["file"] == "j-edit-0.png"
    # LA feuille, relue : jaune (3), rouge (0), rouge (0) — le piège aurait donné jaune, jaune, jaune
    assert _centres(d / "sheet.png", 3, 3, 128) == [COULEURS[3], COULEURS[0], COULEURS[0]]
    with Image.open(d / "frames" / "000.png") as c0:      # la case survit OCTET pour octet (pas de resize, et
        assert c0.convert("RGBA").tobytes() == octets3      # pas d'alpha appliqué deux fois sur les bords doux)
    assert any(0 < a < 255 for a in octets3[3::4])            # …et la case a bien des bords doux à protéger
    # sans `anim`, chaque image garde SA durée
    assert [f["duration_ms"] for f in m["frames"]] == [100, 70, 70]
    assert m["trim"] == "animation" and m["native"] is False     # le manifeste dit la feuille d'ORIGINE
    # les exports ont été réécrits avec les 3 nouvelles cases
    assert (d / "sheet.tres").read_text("utf-8").count('[sub_resource type="AtlasTexture"') == 3
    assert len(json.loads((d / "sheet.paper2dsprites").read_text("utf-8"))["frames"]) == 3
    assert len(json.loads((d / "sheet.atlas.json").read_text("utf-8"))["frames"]) == 3
    total = 0
    with Image.open(d / "preview.gif") as g:            # Pillow fusionne les images identiques consécutives (0, 0)
        for i in range(g.n_frames):                     # en additionnant leurs durées : le TEMPS est ce qui compte
            g.seek(i)
            total += g.info["duration"]
    assert total == 100 + 70 + 70
    assert not (d / "_edit").exists()          # le dossier de travail est parti
    assert not (d / "frames" / "003.png").exists()       # plus de case orpheline sur le disque


def test_les_bornes_de_l_ordre_refusent_en_le_disant_sans_rien_toucher():
    d = _feuille("j-borne")
    avant = (d / "manifest.json").read_bytes()
    for corps in ({"order": []}, {"order": [0, 4]}, {"order": "0"}, {"order": [0] * 65}, {"order": [0] * 65, "anim": {"tags": []}}, {"order": [-1]},
                  {"order": [1.5]}, {"order": [True]}, {"order": ["1"]}, {"order": [0], "columns": 99},
                  {"order": [0], "columns": "x"}, {}):
        st, txt = _post("j-borne", corps)
        assert st == 400, (corps, st, txt)
    assert (d / "manifest.json").read_bytes() == avant
    assert not (d / "_edit").exists()
    assert _post("j-absent", {"order": [0]})[0] == 404


def test_une_sonde_filmstrip_n_est_pas_editable():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"sonde-{i}.png", c) for i, c in enumerate(COULEURS[:2])]
    asyncio.run(S.generate_sprites({"source": {"kind": "images", "filenames": noms}, "extract_only": True}, "j-sonde"))
    assert (settings.outputs_path / "sprites" / "j-sonde" / "manifest.json").is_file()
    st, txt = _post("j-sonde", {"order": [0]})
    assert st == 400 and "grid" in txt, (st, txt)


def test_les_tags_suivent_le_nouvel_ordre():
    d = _feuille("j-tags")
    st, txt = _post("j-tags", {"order": [0, 1, 2], "columns": 3,
                               "anim": {"tags": [{"name": "idle", "from": 0, "to": 2}], "durations": [90, 90, 90]}})
    assert st == 200, txt
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m["anim"]["tags"][0] == {"name": "idle", "from": 0, "to": 2, "direction": "forward", "repeat": 0}
    assert [f["duration_ms"] for f in m["frames"]] == [90, 90, 90]
    assert '&"idle"' in (d / "sheet.tres").read_text("utf-8")
    # un tag qui déborde le NOUVEL ordre est refusé — et la feuille d'avant reste intacte
    avant = (d / "manifest.json").read_bytes()
    st, txt = _post("j-tags", {"order": [0, 1], "anim": {"tags": [{"name": "x", "from": 0, "to": 2}]}})
    assert st == 400 and "to < 2" in txt, (st, txt)
    # sans `anim`, un tag hérité qui déborde est refusé aussi, en le nommant
    st, txt = _post("j-tags", {"order": [0, 1]})
    assert st == 400 and "idle" in txt, (st, txt)
    assert (d / "manifest.json").read_bytes() == avant


def test_l_ecran_porte_l_editeur_et_l_appelle():
    html = (RACINE / "frontend" / "spritelab" / "index.html").read_text(encoding="utf-8")
    js = (RACINE / "frontend" / "spritelab" / "spritelab.js").read_text(encoding="utf-8")
    for i in ("editor", "editInfo", "editApply", "editReset", "editStrip", "editStatus"):
        assert f'id="{i}"' in html, i
    assert "/reassemble`" in js and "editOrder = m.frames.map(f => f.index);" in js
    assert '$("#editApply").onclick = applyEditor;' in js


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
