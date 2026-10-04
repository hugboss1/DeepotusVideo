# -*- coding: utf-8 -*-
"""Card Forge — tâche #83 (plan-cartes T1-T3, 04/10/2026) : les GABARITS D'IMPRIMEUR.
Les pixels, pas les phrases.

Chaque nombre attendu est ÉCRIT EN DUR, relevé sur les portails et JAMAIS recalculé par la formule qu'il vérifie :
  MPC  (makeplayingcards.com, relevé 04/10/2026) : poker 822x1122, bridge 747x1122, tarot 897x1497,
       domino 597x1122, carte de visite 672x1122, micro 447x597 — fond perdu 36 px (« 1/8 in » publié !) ;
  TGC  (thegamecrafter.com/api/tgc/products, relevé 04/10/2026) : PokerDeck 825x1125, BridgeDeck 750x1125,
       Foil/TarotDeck 900x1500, DominoDeck 600x1125, BusinessDeck 675x1125, JumboDeck 1125x1725 ;
  DTC  (drivethrucards) : page 2,75 x 3,75 in, sans traits de coupe, PDF/X-1a.
FORMATS ÉCARTÉS, parce que leurs pixels ne collent PAS (décision de l'utilisateur 04/10 : vérifier chaque format,
griser le reste) : MPC mini (1,75 x 2,5 in contre 44 x 68 mm ici), jumbo (MPC 3,5 x 5 contre 3,5 x 5,5), carré
70 mm, poker EU ; TGC poker EU (TGC impose 825x1125 à son Euro Poker), carré (900 contre 902), mini, micro.

LE PIÈGE, NOMMÉ : MPC publie « fond perdu 1/8 in » ET « 822 x 1122 px ». 1/8 in vaut 37,5 px à 300 DPI, soit
825 x 1125. C'est le PIXEL que le portail contrôle : le profil écrit 3,048 mm, pas 3,175.

DTC (décision 04/10) : SANS profil ICC de presse chargé, le PDF tient les dimensions et NE revendique PAS PDF/X-1a ;
avec un profil de presse (classe « prtr », CMJN), séparation littleCMS, images /DeviceCMYK nues, revendication
écrite ET relue dans les octets.
Témoin positif : la base (bcb9ecfe) n'a aucun gabarit.

Run : cd backend ; & $PY tests/test_cards_gabarits.py
"""
import asyncio
import io
import json
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp(prefix="cfgab_")
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
from app.services.cards import contract as CT                    # noqa: E402

RACINE = _ICI.parent.parent
BASE = "bcb9ecfe"
GRACOL = pathlib.Path(r"C:\Windows\System32\spool\drivers\color\CoatedGRACoL2006.icc")

# ── les seuils relevés, écrits en dur ───────────────────────────────────────
MPC = {"poker_us": (822, 1122), "bridge_us": (747, 1122), "tarot_us": (897, 1497), "domino": (597, 1122),
       "business": (672, 1122), "micro": (447, 597)}
TGC = {"poker_us": (825, 1125), "bridge_us": (750, 1125), "tarot_us": (900, 1500), "domino": (600, 1125),
       "business": (675, 1125), "jumbo": (1125, 1725)}
DTC_PAGE_PT = (198.0, 270.0)          # 2,75 x 3,75 in


def test_temoin_la_base_n_a_aucun_gabarit():
    r = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/contract.py"],
                       capture_output=True, cwd=str(RACINE))
    assert r.returncode == 0 and b"PRINTER_PROFILES" not in r.stdout and b"profile_geom" not in r.stdout


# ─────────────────────── T1 : les gabarits dans le contrat ──────────────────
def test_chaque_format_garde_sort_les_pixels_publies():
    for pid, table in (("mpc", MPC), ("tgc", TGC)):
        for fmt, px in table.items():
            assert tuple(CT.profile_geom(pid, fmt).canvas_px) == px, (pid, fmt, CT.profile_geom(pid, fmt).canvas_px)
    assert tuple(CT.profile_geom("dtc", "poker_us").canvas_px) == (825, 1125)


def test_les_formats_servis_sont_exactement_ceux_verifies():
    assert set(CT.PRINTER_PROFILES["mpc"]["fmts"]) == set(MPC)
    assert set(CT.PRINTER_PROFILES["tgc"]["fmts"]) == set(TGC)
    assert tuple(CT.PRINTER_PROFILES["dtc"]["fmts"]) == ("poker_us",)
    assert set(CT.PRINTER_PROFILES["maison"]["fmts"]) == set(CT.FORMATS)


def test_mpc_ecrit_36_px_et_non_un_huitieme_de_pouce():
    g = CT.profile_geom("mpc", "poker_us")
    assert CT.PRINTER_PROFILES["mpc"]["bleed_mm"] == 3.048
    assert tuple(g.bleed_off_px) == (36.0, 36.0) and tuple(g.safe_off_px) == (72.0, 72.0)
    assert CT.geom("poker_us", 300, 3.175, 3.175).canvas_px == (825, 1125)


def test_tgc_coupe_a_37_5_et_zone_sure_a_75():
    g = CT.profile_geom("tgc", "poker_us")
    assert tuple(g.bleed_off_px) == (37.5, 37.5) and tuple(g.safe_off_px) == (75.0, 75.0)


def test_dtc_fait_exactement_2_75_par_3_75_pouces():
    g = CT.profile_geom("dtc", "poker_us")
    assert (g.canvas_px[0] * 72.0 / g.dpi, g.canvas_px[1] * 72.0 / g.dpi) == DTC_PAGE_PT


def test_un_gabarit_refuse_un_format_non_verifie_en_le_disant():
    for pid, fmt in (("dtc", "square_eu"), ("mpc", "mini"), ("mpc", "jumbo"), ("tgc", "poker_eu"), ("tgc", "micro")):
        with pytest.raises(ValueError) as e:
            CT.profile_geom(pid, fmt)
        assert "n'accepte pas" in str(e.value) and fmt in str(e.value), str(e.value)
    with pytest.raises(ValueError) as e:
        CT.printer_profile("vistaprint")
    assert "vistaprint" in str(e.value) and "mpc" in str(e.value)


def test_maison_garde_le_fond_perdu_natif():
    assert CT.profile_geom("maison", "poker_eu").canvas_px == CT.geom("poker_eu", 300).canvas_px
    assert CT.profile_geom("maison", "poker_us").canvas_px == CT.geom("poker_us", 300).canvas_px


def test_le_catalogue_dit_la_livraison_et_la_revendication():
    tbl = {r["id"]: r for r in CT.profile_table("poker_us")}
    assert list(tbl) == ["maison", "mpc", "tgc", "dtc"]
    assert (tbl["mpc"]["delivery"], tbl["tgc"]["delivery"], tbl["dtc"]["delivery"]) == ("png_zip", "png_zip", "pdf")
    assert tbl["dtc"]["pdfx"] == "PDF/X-1a:2001" and tbl["dtc"]["marks"] == "none"
    assert tbl["mpc"]["geom"]["canvas_px"] == [822, 1122]
    assert tbl["mpc"]["verifie"] and "04/10/2026" in tbl["mpc"]["verifie"]
    carre = {r["id"]: r for r in CT.profile_table("square_eu")}
    assert carre["dtc"]["geom"] is None and carre["mpc"]["geom"] is None and carre["maison"]["geom"] is not None


# ─────────────────────── T2 : le paquet imprimeur ───────────────────────────
def _png(w, h, rgb=(18, 24, 32)):
    b = io.BytesIO()
    Image.new("RGB", (w, h), rgb).save(b, "PNG")
    return b.getvalue()


def _ihdr(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def _phys(data):
    i = 8
    while i < len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        if data[i + 4:i + 8] == b"pHYs":
            return struct.unpack(">II", data[i + 8:i + 16])[0]
        i += 12 + ln
    return None


async def _client_deck(c, name, fmt):
    r = await c.post("/api/cards/decks", json={"name": name})
    did = r.json()["deck"]["id"]
    await c.patch(f"/api/cards/{did}", json={"format": {"fmt": fmt, "dpi": 300}})
    return did


def _paquet(profil, n=3, fmt="poker_us", name="Banc gabarit", px=None, backs=True, spec=None):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            did = await _client_deck(c, name, fmt)
            w, h = px or CT.profile_geom(profil, fmt).canvas_px
            files = [("fronts", (f"f{i}.png", _png(w, h, (10 + i, 20, 30)), "image/png")) for i in range(n)]
            if backs:
                files += [("backs", (f"b{i}.png", _png(w, h, (200, 20 + i, 30)), "image/png")) for i in range(n)]
            return await c.post(f"/api/cards/{did}/print/pack", data={"spec": json.dumps(spec or {"profile": profil})},
                                files=files, timeout=120.0)
    return asyncio.run(go())


def test_le_paquet_mpc_nomme_recto_verso_et_fait_822x1122():
    r = _paquet("mpc", 3)
    assert r.status_code == 200, r.text
    z = zipfile.ZipFile(io.BytesIO(r.content))
    noms = z.namelist()
    assert noms[0] == "mpc/manifeste.json", noms
    cartes = sorted(n for n in noms if n.endswith(".png"))
    assert cartes == ["mpc/banc-gabarit_01_recto.png", "mpc/banc-gabarit_01_verso.png",
                      "mpc/banc-gabarit_02_recto.png", "mpc/banc-gabarit_02_verso.png",
                      "mpc/banc-gabarit_03_recto.png", "mpc/banc-gabarit_03_verso.png"], cartes
    for n in cartes:                      # LE PIXEL, RELU DANS LE FICHIER ÉCRIT
        assert _ihdr(z.read(n)) == (822, 1122), n
        assert _phys(z.read(n)) == 11811, n            # 300 DPI en pixels par mètre
    # l'appariement : la carte 2 recto est bien la 2e reçue (couleur témoin), son verso la 2e verso
    assert Image.open(io.BytesIO(z.read("mpc/banc-gabarit_02_recto.png"))).convert("RGB").getpixel((400, 500)) == (11, 20, 30)
    assert Image.open(io.BytesIO(z.read("mpc/banc-gabarit_02_verso.png"))).convert("RGB").getpixel((400, 500)) == (200, 21, 30)
    assert r.headers["X-CF-Pixels"] == "822x1122" and r.headers["X-CF-Cards"] == "3"
    assert 'filename="paquet_mpc.zip"' in r.headers["Content-Disposition"]


def test_le_paquet_tgc_fait_825x1125_et_le_jumbo_1125x1725():
    for fmt, px in (("poker_us", (825, 1125)), ("jumbo", (1125, 1725))):
        r = _paquet("tgc", 2, fmt=fmt)
        assert r.status_code == 200, r.text
        z = zipfile.ZipFile(io.BytesIO(r.content))
        pngs = [x for x in z.namelist() if x.endswith(".png")]
        assert len(pngs) == 4 and all(_ihdr(z.read(n)) == px for n in pngs), (fmt, pngs)


def test_le_zero_comblement_suit_la_taille_du_deck():
    r = _paquet("tgc", 12, backs=False, name="Éclair d'été !")
    assert r.status_code == 200, r.text
    noms = [n for n in zipfile.ZipFile(io.BytesIO(r.content)).namelist() if n.endswith(".png")]
    assert noms[0] == "tgc/eclair-d-ete_01_recto.png" and "tgc/eclair-d-ete_12_recto.png" in noms, noms
    assert not any("verso" in n for n in noms)
    r = _paquet("tgc", 101, backs=False, name="Gros")
    noms = [n for n in zipfile.ZipFile(io.BytesIO(r.content)).namelist() if n.endswith(".png")]
    assert "tgc/gros_001_recto.png" in noms and "tgc/gros_101_recto.png" in noms, noms[:3]


def test_le_manifeste_dit_ce_que_le_paquet_contient():
    r = _paquet("mpc", 2)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    man = json.loads(z.read("mpc/manifeste.json").decode("utf-8"))
    assert (man["profil"], man["canvas_px"], man["bleed_off_px"], man["dpi"], man["fmt"]) == \
        ("mpc", [822, 1122], [36.0, 36.0], 300, "poker_us")
    assert len(man["fichiers"]) == 4
    import hashlib
    for f in man["fichiers"]:
        assert f["sha256"] == hashlib.sha256(z.read("mpc/" + f["nom"])).hexdigest()
        assert f["side"] in ("recto", "verso") and f["px"] == [822, 1122]


def test_un_bitmap_a_la_mauvaise_taille_est_refuse_en_le_disant():
    r = _paquet("mpc", 1, px=(825, 1125), name="Mauvais")
    assert r.status_code == 400, r.status_code
    assert "822" in r.text and "825" in r.text, r.text


def test_un_format_non_verifie_ou_un_gabarit_inconnu_est_refuse():
    r = _paquet("mpc", 1, fmt="mini", px=(592, 875))
    assert r.status_code == 400 and "n'accepte pas" in r.text, r.text
    r = _paquet("mpc", 1, spec={"profile": "vistaprint"})
    assert r.status_code == 400 and "vistaprint" in r.text, r.text
    r = _paquet("dtc", 1)
    assert r.status_code == 400 and "PDF" in r.text, r.text      # DTC se livre en PDF, pas en paquet


def test_sans_carte_le_paquet_est_refuse():
    r = _paquet("mpc", 0, backs=False)
    assert r.status_code == 400 and "Aucune carte" in r.text, r.text


# ─────────────────────── T3 : le PDF DriveThruCards ─────────────────────────
def _pdf(n=2, profil="dtc", icc=None, extra=None):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            did = await _client_deck(c, "Banc DTC", "poker_us")
            if icc:
                ri = await c.post(f"/api/cards/{did}/print/icc", files={"file": ("p.icc", icc, "application/octet-stream")})
                assert ri.status_code == 200, ri.text
            w, h = CT.profile_geom(profil, "poker_us").canvas_px
            files = [("fronts", (f"f{i}.png", _png(w, h), "image/png")) for i in range(n)]
            sp = dict({"profile": profil, "force": True}, **(extra or {}))
            return await c.post(f"/api/cards/{did}/print/pdf", data={"spec": json.dumps(sp)}, files=files, timeout=180.0)
    return asyncio.run(go())


def test_le_pdf_dtc_fait_198_sur_270_points_sans_trait_de_coupe():
    r = _pdf(2)
    assert r.status_code == 200, r.text
    rd = PdfReader(io.BytesIO(r.content))
    assert len(rd.pages) == 2
    for pg in rd.pages:
        assert [float(v) for v in pg.mediabox] == [0.0, 0.0, 198.0, 270.0]
        assert [round(float(v), 4) for v in pg.trimbox] == [9.0, 9.0, 189.0, 261.0]
    assert r.headers["X-CF-Mark-Clearance"].split("/")[1] == "0", r.headers["X-CF-Mark-Clearance"]
    assert r.headers["X-CF-Profile"] == "dtc"


def test_le_pdf_dtc_recto_verso_alterne_une_face_par_page():
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            did = await _client_deck(c, "Banc DTC RV", "poker_us")
            files = [("fronts", (f"f{i}.png", _png(825, 1125, (250, 0, 0)), "image/png")) for i in range(2)]
            files += [("backs", (f"b{i}.png", _png(825, 1125, (0, 0, 250)), "image/png")) for i in range(2)]
            sp = {"profile": "dtc", "force": True, "duplex": True, "duplex_order": "interleave"}
            return await c.post(f"/api/cards/{did}/print/pdf", data={"spec": json.dumps(sp)}, files=files, timeout=180.0)
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    rd = PdfReader(io.BytesIO(r.content))
    assert len(rd.pages) == 4 and all([float(v) for v in pg.mediabox] == [0.0, 0.0, 198.0, 270.0] for pg in rd.pages)


def test_sans_profil_de_presse_le_pdf_dtc_ne_revendique_rien():
    """DÉCISION 04/10 : dimensions tenues, revendication ABSENTE — la conversion CMJN d'appareil de Pillow n'a ni
    retrait des sous-couleurs ni noir squelette. Même avec une intention de registre (GRACoL), on ne promet rien."""
    for extra in ({}, {"intent": "gracol"}):
        r = _pdf(1, extra=extra)
        assert r.status_code == 200, r.text
        assert b"PDF/X-1a" not in r.content and b"GTS_PDFXVersion" not in r.content, extra
        assert r.headers["X-CF-Pdfx"] == "aucune" and r.headers["X-CF-Color"] == "cmyk_device", dict(r.headers)
        assert r.content[:8] == b"%PDF-1.4"


@pytest.mark.skipif(not GRACOL.is_file(), reason="profil de presse Windows absent")
def test_avec_un_profil_de_presse_x1a_est_revendique_et_relu():
    r = _pdf(1, icc=GRACOL.read_bytes())
    assert r.status_code == 200, r.text
    assert r.headers["X-CF-Pdfx"] == "PDF/X-1a:2001", r.headers["X-CF-Pdfx"]
    assert r.headers["X-CF-Color"] == "cmyk_icc"
    assert b"pdfxid:GTS_PDFXVersion>PDF/X-1a:2001" in r.content
    assert r.content[:8] == b"%PDF-1.4" and r.headers["X-CF-Layers"] == "aucun"
    assert r.headers["X-CF-Trapped"] == "/False"
    rd = PdfReader(io.BytesIO(r.content))
    # X-1a : AUCUN /ICCBased dans le CONTENU — les images sont /DeviceCMYK nues, le profil vit dans l'intention
    for pg in rd.pages:
        for _n, xo in (pg["/Resources"].get("/XObject") or {}).items():
            o = xo.get_object()
            if o.get("/Subtype") == "/Image":
                assert o["/ColorSpace"] == "/DeviceCMYK", o["/ColorSpace"]
    oi = rd.trailer["/Root"]["/OutputIntents"][0].get_object()
    assert oi["/S"] == "/GTS_PDFX" and "/DestOutputProfile" in oi
    # L'AUDIT RELIT LES OCTETS : un /ICCBased glissé dans le contenu (même longueur, xref intact) retire la
    # revendication X-1a — l'écran ne peut pas afficher une conformité que le fichier contredit.
    from app.services.cards import print as PRN
    assert PRN.pdf_audit(r.content)["pdfx"] == "PDF/X-1a:2001"
    k = r.content.find(b"/DeviceCMYK")
    assert k > 0
    faux = r.content[:k] + b"/ICCBased  " + r.content[k + 11:]
    assert len(faux) == len(r.content) and PRN.pdf_audit(faux)["pdfx"] == ""


def test_maison_reste_en_x3_et_ne_change_pas():
    """La revendication historique : rien ne bouge pour qui n'a pas choisi de gabarit."""
    if not GRACOL.is_file():
        pytest.skip("profil de presse Windows absent")
    r = _pdf(1, profil="maison", icc=GRACOL.read_bytes(),
             extra={"color": "cmyk_icc", "intent": "icc", "layers": False, "sheet": "card"})
    assert r.status_code == 200, r.text
    assert r.headers["X-CF-Pdfx"] == "PDF/X-3:2003", r.headers["X-CF-Pdfx"]


def test_le_controle_avant_vol_nomme_le_gabarit():
    r = _pdf(1)
    assert "gabarit dtc" in r.headers["X-CF-Control"].lower(), r.headers["X-CF-Control"]


def test_une_revision_pdfx_inconnue_est_refusee():
    r = _pdf(1, profil="maison", extra={"pdfx": "PDF/X-4"})
    assert r.status_code == 400 and "PDF/X-4" in r.text and "PDF/X-1a:2001" in r.text, r.text


def test_mpc_et_tgc_ne_se_livrent_pas_en_pdf():
    r = _pdf(1, profil="mpc")
    assert r.status_code == 400 and "paquet" in r.text.lower(), r.text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
