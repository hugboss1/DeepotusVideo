# -*- coding: utf-8 -*-
"""Card Forge — tâche #85 PR A (plan-cartes T8, 04/10/2026) : D'OÙ VIENT LE DOS de chaque carte, et la MIRE.

1. `card.back` a DEUX lecteurs : P2 (mod-frame.js `backOf`) y cherche un MOTIF du catalogue (frame.BACKS) — et
   seulement si « dos commun » est DÉCOCHÉ ; P1 (mod-face.js `resolveArtId`) y cherche une ILLUSTRATION
   (cat:…, local:…, img:nom ou nom nu de la Bibliothèque). Une valeur qui n'est ni l'un ni l'autre retombait sur le
   dos commun SANS UN MOT. Le compte rendu le dit, par valeur, en CARTES (quantités appliquées).
   Le plan lisait les motifs dans `CF.get("frame.backs_ids")` — clé qui N'EXISTE PAS : le serveur lit frame.BACKS.
2. La mire mesure la MACHINE (`mirror_um` mesure le fichier). Le plan décalait une graduation d'un demi-pas : ce
   n'est pas un vernier, rien ne s'y lit. Ici un VRAI vernier : traits au millimètre au recto, à 0,9 mm au verso —
   le trait qui coïncide donne le dixième. Symétrique autour du centre : indifférent au sens de retournement.
Témoin positif : la base (5e837e61) n'a ni /data/dos ni /print/mire.
Run : cd backend ; & $PY tests/test_cards_dos.py
"""
import asyncio
import io
import os
import pathlib
import re
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp(prefix="cfdos_")
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
from PIL import Image                                            # noqa: E402
from pypdf import PdfReader                                      # noqa: E402

RACINE = _ICI.parent.parent
BASE = "5e837e61"
Image.new("RGB", (10, 10), (1, 2, 3)).save(pathlib.Path(_tmp, "images", "mon_dos.png"))


def test_temoin_la_base_n_a_ni_dos_ni_mire():
    d = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/data.py"], capture_output=True, cwd=str(RACINE)).stdout
    p = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/print.py"], capture_output=True, cwd=str(RACINE)).stdout
    assert d and p and b'@router.post("/dos")' not in d and b'@router.get("/mire")' not in p


def _dos(table, frame=None, corps=None):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Dos"})
            did = r.json()["deck"]["id"]
            if frame is not None:
                await c.patch(f"/api/cards/{did}", json={"frame": frame})
            return await c.post(f"/api/cards/{did}/data/dos", json=corps if corps is not None else table)
    return asyncio.run(go())


TABLE = {"columns": ["nom", "dos", "qty"],
         "rows": [["Colosse", "lattice", "2"], ["Oracle", "mon_dos.png", "1"], ["Oracle bis", "img:mon_dos.png", "1"],
                  ["Rebut", "", "3"], ["Echo", "inconnu_xyz", "1"], ["Locale", "local:k9", "1"],
                  ["Cat", "cat:face_azur_vista_feu", "1"], ["Écartée", "inconnu_xyz", "5"]],
         "back_col": "dos", "qty_col": "qty", "off": [7]}


def test_l_origine_du_dos_est_dite_par_valeur_en_cartes():
    r = _dos(TABLE, frame={"back_same": False})
    assert r.status_code == 200, r.text
    j = r.json()
    par = {d["valeur"]: d for d in j["dos"]}
    assert par["lattice"]["origine"] == "motif" and par["lattice"]["cartes"] == 2
    assert par["mon_dos.png"]["origine"] == "image" and par["img:mon_dos.png"]["origine"] == "image"
    assert par[""]["origine"] == "commun" and par[""]["cartes"] == 3
    assert par["local:k9"]["origine"] == "image_locale"
    assert par["cat:face_azur_vista_feu"]["origine"] == "image"
    assert par["inconnu_xyz"]["origine"] == "introuvable" and par["inconnu_xyz"]["cartes"] == 1   # la ligne écartée ne compte pas
    assert j["total_cartes"] == 10 and j["colonne"] == "dos" and j["dos_commun"] is False
    assert any("inconnu_xyz" in a and "DOS COMMUN" in a for a in j["avertissements"]), j["avertissements"]
    assert [d["cartes"] for d in j["dos"]] == sorted((d["cartes"] for d in j["dos"]), reverse=True)


def test_dos_commun_coche_un_motif_est_ignore_et_c_est_dit():
    r = _dos(TABLE)                                  # le défaut de la pièce 02 : « dos commun » coché
    j = r.json()
    par = {d["valeur"]: d for d in j["dos"]}
    assert j["dos_commun"] is True and par["lattice"]["origine"] == "motif_ignore", par["lattice"]
    assert any("lattice" in a and "Dos commun" in a for a in j["avertissements"]), j["avertissements"]
    # une illustration, elle, est lue par la pièce 01 quel que soit ce réglage
    assert par["mon_dos.png"]["origine"] == "image"


def test_les_motifs_sont_ceux_du_catalogue_de_la_piece_02():
    from app.services.cards import frame as P2
    ids = [b["id"] for b in P2.BACKS]
    r = _dos({"columns": ["dos"], "rows": [[i] for i in ids] + [["quadrillage"]]}, frame={"back_same": False})
    par = {d["valeur"]: d["origine"] for d in r.json()["dos"]}
    assert all(par[i] == "motif" for i in ids) and par["quadrillage"] == "introuvable", par


def test_sans_colonne_de_dos_tout_est_commun_et_c_est_dit():
    r = _dos({"columns": ["nom", "qty"], "rows": [["a", "2"], ["b", "1"]], "qty_col": "qty"})
    j = r.json()
    assert j["colonne"] == "" and j["total_cartes"] == 3 and j["dos"] == [
        {"valeur": "", "lignes": 2, "cartes": 3, "origine": "commun"}], j
    assert any("Aucune colonne" in a for a in j["avertissements"])
    r = _dos({"columns": ["Back", "x"], "rows": [["lattice", "1"]]}, frame={"back_same": False})
    assert r.json()["colonne"] == "Back"                 # « dos » / « back » reconnus sans mappage


def test_un_corps_mal_forme_fait_400():
    assert _dos(None, corps={"columns": "x"}).status_code == 400
    r = _dos(None, corps={"columns": ["a"], "rows": [["1"]], "back_col": "absente"})
    assert r.status_code == 400 and "Colonne de dos inconnue : 'absente'" in r.text, r.text


# ─────────────────────────────── la mire ────────────────────────────────────
MM = 72.0 / 25.4


def _mire(q="sheet=a4"):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Mire"})
            did = r.json()["deck"]["id"]
            return await c.get(f"/api/cards/{did}/print/mire?{q}")
    return asyncio.run(go())


def _segments(page):
    data = page.get_contents().get_data().decode("latin-1")
    return [tuple(map(float, m)) for m in re.findall(r"(-?[\d.]+) (-?[\d.]+) m (-?[\d.]+) (-?[\d.]+) l S", data)]


def test_la_mire_est_deux_pages_vectorielles_a_la_taille_de_la_feuille():
    r = _mire()
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    rd = PdfReader(io.BytesIO(r.content))
    assert len(rd.pages) == 2
    assert [round(float(v), 2) for v in rd.pages[0].mediabox] == [0.0, 0.0, 595.2, 841.92]
    assert b"/Image" not in r.content and b"/Font" not in r.content          # que des traits : rien de rééchantillonné
    assert r.headers["X-CF-Mire-Resolution-Mm"] == "0,1" and r.headers["X-CF-Mire-Etendue-Mm"] == "10"
    assert 'filename="mire_recto_verso_a4.pdf"' in r.headers["Content-Disposition"]
    rl = _mire("sheet=letter")
    assert [round(float(v), 1) for v in PdfReader(io.BytesIO(rl.content)).pages[0].mediabox][2:] == [612.0, 792.0]


def test_la_mire_est_un_vrai_vernier_au_dixieme():
    rd = PdfReader(io.BytesIO(_mire().content))
    W, H = (float(v) for v in rd.pages[0].mediabox[2:])
    cx, cy = W / 2, H / 2
    pas = {}
    for n, page in enumerate(rd.pages):
        # les traits VERTICAUX de l'échelle horizontale, juste au-dessus du centre (bande y in [cy+20 mm, cy+30 mm])
        xs = sorted({round(x0 - cx, 2) for x0, y0, x1, y1 in _segments(page)
                     if abs(x0 - x1) < 1e-6 and cy + 19 * MM < min(y0, y1) < cy + 31 * MM and abs(x0 - cx) < 11 * MM})
        pas[n] = xs
    rec = [k * 1.0 * MM for k in range(-10, 11)]
    ver = [k * 0.9 * MM for k in range(-10, 11)]
    # recto : les traits partent de la ligne de base (25 mm) en S'ÉLOIGNANT du centre ; verso : en s'en
    # RAPPROCHANT — superposés, les deux échelles se TOUCHENT sur la ligne de base au lieu de se chevaucher
    for n, page in enumerate(rd.pages):
        hauts = [(min(y0, y1), max(y0, y1)) for x0, y0, x1, y1 in _segments(page)
                 if abs(x0 - x1) < 1e-6 and abs(x0 - cx) < 11 * MM and cy + 19 * MM < min(y0, y1) < cy + 31 * MM]
        base = cy + 25 * MM
        if n == 0:
            assert all(abs(lo - base) < 0.05 and hi > base + 1 for lo, hi in hauts), hauts[:3]
        else:
            assert all(abs(hi - base) < 0.05 and lo < base - 1 for lo, hi in hauts), hauts[:3]
    assert len(pas[0]) == 21 and all(abs(a - b) < 0.01 for a, b in zip(pas[0], rec)), pas[0]
    assert len(pas[1]) == 21 and all(abs(a - b) < 0.01 for a, b in zip(pas[1], ver)), pas[1]
    # le vernier : un décalage de 0,3 mm fait coïncider le TROISIÈME trait compté depuis le zéro, du côté du
    # décalage (un vernier se répète tous les 10 traits : de l'autre côté, c'est le -7) — ce que la page apprend à lire
    for d10 in range(0, 10):
        d = d10 / 10 * MM
        k = min(range(0, 11), key=lambda k: min(abs(k * 0.9 * MM + d - m) for m in rec))
        assert k == d10, (d10, k)


def test_la_mire_dit_comment_la_lire_et_la_verticale_est_graduee_aussi():
    rd = PdfReader(io.BytesIO(_mire().content))
    W, H = (float(v) for v in rd.pages[0].mediabox[2:])
    cx = W / 2
    for page, p in ((rd.pages[0], 1.0), (rd.pages[1], 0.9)):
        ys = sorted({round(y0 - H / 2, 2) for x0, y0, x1, y1 in _segments(page)
                     if abs(y0 - y1) < 1e-6 and cx + 19 * MM < min(x0, x1) < cx + 31 * MM and abs(y0 - H / 2) < 11 * MM})
        att = [k * p * MM for k in range(-10, 11)]
        assert len(ys) == 21 and all(abs(a - b) < 0.01 for a, b in zip(ys, att)), ys
        assert page.get_contents().get_data().count(b" S") > 150                # texte tracé compris


def test_retournee_par_le_bord_long_ou_court_chaque_echelle_du_verso_retombe_sur_celle_du_recto():
    """Vu sur l'aperçu de la preuve : une échelle posée d'UN seul côté du centre ne recouvre pas la sienne une
    fois la feuille retournée (bord long : gauche <-> droite ; bord court : haut <-> bas). On simule le
    retournement sur les traits écrits et on exige que chaque ligne de base du verso tombe sur une du recto."""
    rd = PdfReader(io.BytesIO(_mire().content))
    W, H = (float(v) for v in rd.pages[0].mediabox[2:])

    def bases(page, fx=lambda x: x, fy=lambda y: y):
        segs = [(fx(a), fy(b), fx(c), fy(d)) for a, b, c, d in _segments(page)]
        cx, cy = W / 2, H / 2
        # lignes de base = l'extrémité commune des traits d'échelle, à 25 mm du centre
        hs = {round(y0 if abs(abs(y0 - cy) - 25 * MM) < 0.05 else y1, 1) for x0, y0, x1, y1 in segs
              if abs(x0 - x1) < 1e-6 and abs(x0 - cx) < 11 * MM and (abs(abs(y0 - cy) - 25 * MM) < 0.05 or abs(abs(y1 - cy) - 25 * MM) < 0.05)}
        vs = {round(x0 if abs(abs(x0 - cx) - 25 * MM) < 0.05 else x1, 1) for x0, y0, x1, y1 in segs
              if abs(y0 - y1) < 1e-6 and abs(y0 - cy) < 11 * MM and (abs(abs(x0 - cx) - 25 * MM) < 0.05 or abs(abs(x1 - cx) - 25 * MM) < 0.05)}
        return hs, vs
    r_h, r_v = bases(rd.pages[0])
    assert len(r_h) == 2 and len(r_v) == 2, (r_h, r_v)                    # dessus/dessous, gauche/droite
    for nom, fx, fy in (("bord long", lambda x: W - x, lambda y: y), ("bord court", lambda x: x, lambda y: H - y)):
        v_h, v_v = bases(rd.pages[1], fx, fy)
        assert v_h == r_h and v_v == r_v, (nom, v_h, r_h, v_v, r_v)


def test_une_feuille_inconnue_fait_400():
    r = _mire("sheet=tabloid")
    assert r.status_code == 400 and "Planche inconnue : 'tabloid'" in r.text and "a4" in r.text, r.text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
