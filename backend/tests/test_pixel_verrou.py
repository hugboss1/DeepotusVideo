"""t340 (lot Scenario, B1 + B2) — grille pixel EXACTE et palette IMPOSÉES par l'outil, sprite « approuvé » qui les
verrouille, préréglage « Boucle ».

Relevé Scenario (scroll-courier) : la grille vient d'un OUTIL (Pixelate), jamais du modèle ; un sprite approuvé
(Pixel Lock) fige grille et palette pour les poses et les animations suivantes ; Animate Loop = même pose en 1re et
dernière image (Seedance), puis 1 image sur 2-3, re-pixelisées, feuille + GIF.

LA PREUVE : `pixel_ops.verifier_pixel` contrôle que chaque bloc est UNI et chaque couleur dans la palette ; le banc le
rejoue indépendamment sur les cases écrites. La vidéo est SIMULÉE (pipeline.run remplacé) : aucun appel payant.

Run: python tests/test_pixel_verrou.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzpxv_")
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


# ── images de test : des sprites « photo » (milliers de couleurs, bords doux) sur fond transparent ──────────────
def _sprite(nom: str, teinte: int, taille=(120, 90), decal=0):
    from app.config import settings
    w, h = taille
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    px = im.load()
    for y in range(h):
        for x in range(w):
            dx, dy = (x - w / 2 - decal) / (w * 0.4), (y - h / 2) / (h * 0.4)
            if dx * dx + dy * dy <= 1:
                px[x, y] = ((teinte + 2 * x) % 256, (3 * y + teinte // 2) % 256, (x * y + teinte) % 256, 255)
    im = im.resize((w, h), Image.LANCZOS)
    im.save(settings.images_path / nom)
    return nom


def _run(payload, job):
    from app.services import sprite_service as S
    return asyncio.run(S.generate_sprites(payload, job))


def _manifest(job):
    from app.config import settings
    return json.loads((settings.outputs_path / "sprites" / job / "manifest.json").read_text("utf-8"))


def _frames(job):
    from app.config import settings
    d = settings.outputs_path / "sprites" / job
    out = []
    for f in _manifest(job)["frames"]:
        with Image.open(d / f["file"]) as im:
            out.append(im.convert("RGBA"))
    return out


# ── pixel_ops : palette explicite et vérificateur (purs) ────────────────────────────────────────────────────────
def test_palette_hex_normalisee_exclusive_et_bornee():
    from app.services.pixel_ops import normalize_pixel_opts
    o = normalize_pixel_opts({"target_px": 32, "palette_hex": ["#ff0000", "00FF00", "#FF0000"]})
    assert o == {"target_px": 32, "colors": None, "palette": None, "dither": "none", "scale": 1,
                 "palette_hex": ["#FF0000", "#00FF00"]}
    for bad in ({"palette_hex": ["#FF0000"]}, {"palette_hex": ["#GG0000", "#000000"]},
                {"palette_hex": "#FF0000,#000000"}, {"palette_hex": ["#FF0000", "#000000"], "palette": "pico8"},
                {"palette_hex": ["#FF0000", "#000000"], "colors": 4},
                {"palette_hex": [f"#{i:06X}" for i in range(257)]}):
        with pytest.raises(ValueError):
            normalize_pixel_opts(bad)
    # sans palette_hex, les options d'avant sont inchangées (aucune clé de plus)
    assert "palette_hex" not in normalize_pixel_opts({})


def test_pixelate_sur_palette_explicite_reste_dans_la_palette():
    from app.services.pixel_ops import normalize_pixel_opts, pixelate, palette_utilisee
    from app.config import settings
    pal = ["#1A1C2C", "#B13E53", "#FFCD75", "#38B764", "#41A6F6", "#F4F4F4"]
    with Image.open(settings.images_path / _sprite("pv_pal.png", 10)) as src:
        for dither in ("none", "ordered", "floyd"):
            out = pixelate(src, normalize_pixel_opts({"target_px": 40, "palette_hex": pal, "dither": dither}))
            assert set(palette_utilisee(out)) <= set(pal), dither


def test_verifier_pixel_voit_un_bloc_non_uni_une_couleur_hors_palette_et_l_alpha_partiel():
    from app.services.pixel_ops import normalize_pixel_opts, pixelate, verifier_pixel
    from app.config import settings
    with Image.open(settings.images_path / _sprite("pv_ver.png", 60)) as src:
        out = pixelate(src, normalize_pixel_opts({"target_px": 24, "palette": "sweetie16", "scale": 4}))
    from app.services.pixel_ops import PALETTES
    v = verifier_pixel(out, 4, PALETTES["sweetie16"])
    assert v["ok"] and v["blocs_non_unis"] == 0 and v["hors_palette"] == 0 and v["bloc"] == 4, v
    assert v["blocs"] == (out.width // 4) * (out.height // 4)
    # un seul pixel touché : un bloc non uni ET une couleur hors palette
    abime = out.copy()
    abime.putpixel((5, 5), (1, 2, 3, 255))
    v = verifier_pixel(abime, 4, PALETTES["sweetie16"])
    assert v["blocs_non_unis"] == 1 and v["hors_palette"] == 1 and v["pixels_hors_palette"] == 1 and not v["ok"]
    # même image décalée de 3 px : avec la bonne origine elle passe, sans elle non
    toile = Image.new("RGBA", (out.width + 8, out.height + 8), (0, 0, 0, 0))
    toile.paste(out, (3, 2))
    assert verifier_pixel(toile, 4, PALETTES["sweetie16"], (3, 2))["ok"]
    assert verifier_pixel(toile, 4, PALETTES["sweetie16"], (0, 0))["blocs_non_unis"] > 0
    # alpha partiel
    demi = out.copy()
    demi.putpixel((0, 0), (0x1A, 0x1C, 0x2C, 128))
    assert verifier_pixel(demi, 1, PALETTES["sweetie16"])["alpha_partiel"] == 1


def test_palette_utilisee_ignore_le_transparent_et_refuse_la_photo():
    from app.services.pixel_ops import palette_utilisee
    im = Image.new("RGBA", (4, 1), (9, 9, 9, 0))
    im.putpixel((0, 0), (255, 0, 0, 255))
    im.putpixel((1, 0), (0, 0, 255, 255))
    assert palette_utilisee(im) == ["#0000FF", "#FF0000"]
    photo = Image.new("RGBA", (300, 1))
    for x in range(300):
        photo.putpixel((x, 0), (x % 256, x // 256, 7, 255))
    with pytest.raises(ValueError, match="256"):
        palette_utilisee(photo)


# ── la feuille : grille EXACTE (facteur entier) prouvée case par case ─────────────────────────────────────────
def test_feuille_pixel_grille_exacte_facteur_entier_et_preuve_au_manifeste():
    from app.services.pixel_ops import PALETTES, verifier_pixel
    noms = [_sprite(f"pv_g{i}.png", 30 * i, decal=i) for i in range(4)]
    _run({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 256},
          "pixel": {"target_px": 48, "palette": "pico8"}}, "aa000001")
    m = _manifest("aa000001")
    # 120×90 -> grille 48×36 ; 256 / 48 = 5,33 : la case reçoit ×5 (240×180), JAMAIS ×5,33
    assert m["pixel_verif"]["bloc"] == 5, m["pixel_verif"]
    assert m["pixel_verif"]["ok"] and m["pixel_verif"]["frames"] == 4 and m["pixel_verif"]["palette"] == 16
    for fr in _frames("aa000001"):
        v = verifier_pixel(fr, 5, PALETTES["pico8"], (8, 38))     # (256-240)//2, (256-180)//2
        assert v["ok"], v
        assert fr.getchannel("A").getbbox() is not None


def test_feuille_sans_pixel_inchangee():
    noms = [_sprite("pv_np.png", 3)]
    _run({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128}}, "aa000002")
    m = _manifest("aa000002")
    assert "pixel_verif" not in m and "pixel_verrou" not in m and m["pixel"] is None


# ── B1 : le sprite approuvé verrouille grille + palette ──────────────────────────────────────────────────────
def test_approuver_fige_la_palette_reellement_posee_puis_l_impose():
    from app.services import sprite_service as S
    from app.services.pixel_ops import verifier_pixel, palette_utilisee
    noms = [_sprite(f"pv_a{i}.png", 40 * i) for i in range(3)]
    _run({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128},
          "pixel": {"target_px": 32, "colors": 12}}, "bb000001")
    a = S.approuver("bb000001")
    assert a["target_px"] == 32 and a["palette_origine"] == "sprite" and 2 <= len(a["palette_hex"]) <= 12 * 3
    assert a["palette_hex"] == palette_utilisee(_frames("bb000001"))
    assert S.lire_approbation("bb000001") == a
    # une AUTRE animation, d'autres couleurs, et un `pixel` client contraire : le verrou gagne
    autres = [_sprite(f"pv_b{i}.png", 130 + 25 * i, decal=2 * i) for i in range(4)]
    _run({"source": {"kind": "images", "filenames": autres}, "cell": {"size": 128},
          "pixel": {"target_px": 16, "palette": "gameboy"}, "pixel_verrou": "bb000001"}, "bb000002")
    m = _manifest("bb000002")
    assert m["pixel"]["target_px"] == 32 and m["pixel"]["palette_hex"] == a["palette_hex"]
    assert m["pixel"]["palette"] is None and m["pixel"]["colors"] is None
    assert m["pixel_verrou"] == {"job": "bb000001", "target_px": 32, "palette": None,
                                 "n_couleurs": len(a["palette_hex"])}
    assert m["pixel_verif"]["ok"] and m["pixel_verif"]["palette"] == len(a["palette_hex"])
    assert m["pixel_verif"]["bloc"] == 4                                       # 128 / 32
    assert set(palette_utilisee(_frames("bb000002"))) <= set(a["palette_hex"]), "toute couleur vient du verrou"
    for fr in _frames("bb000002"):
        assert verifier_pixel(fr, 4, a["palette_hex"], (0, 16))["ok"]       # 32×24 -> 128×96, y = (128-96)//2


def test_approuver_une_palette_nommee_la_garde_entiere():
    from app.services import sprite_service as S
    _run({"source": {"kind": "images", "filenames": [_sprite("pv_n.png", 77)]}, "cell": {"size": 128},
          "pixel": {"target_px": 32, "palette": "sweetie16", "dither": "ordered"}}, "bb000003")
    a = S.approuver("bb000003")
    assert a["palette"] == "sweetie16" and a["palette_origine"] == "nommee" and len(a["palette_hex"]) == 16
    assert a["palette_hex"][0] == "#1A1C2C" and a["dither"] == "ordered"


def test_approuver_refuse_sans_pixel_art_et_les_ids_douteux():
    from app.services import sprite_service as S
    _run({"source": {"kind": "images", "filenames": [_sprite("pv_r.png", 5)]}, "cell": {"size": 128}}, "bb000004")
    with pytest.raises(ValueError, match="Pixel art"):
        S.approuver("bb000004")
    with pytest.raises(FileNotFoundError):
        S.approuver("0badc0de")
    for bad in ("../x", "BB00", "", "zzzzzzzz"):
        with pytest.raises(ValueError):
            S.approuver(bad)
    with pytest.raises(ValueError, match="not approved"):
        S.normalize_opts({"pixel_verrou": "bb000004"})


# ── B2 : le préréglage « Boucle » ───────────────────────────────────────────────────────────────────────────
def _film(prefixe, n, fermee):
    noms = [_sprite(f"{prefixe}{i}.png", 20 * i, decal=i) for i in range(n - 1)]
    noms.append(noms[0] if fermee else _sprite(f"{prefixe}fin.png", 250, decal=9))
    return noms


def test_boucle_une_sur_deux_et_la_derniere_pose_retiree():
    noms = _film("pv_l", 9, fermee=True)
    _run({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128}, "boucle": {"une_sur": 2},
          "pixel": {"target_px": 32, "palette": "pico8"}}, "cc000001")
    m = _manifest("cc000001")
    assert m["source"]["boucle"] == {"une_sur": 2, "fermee": True, "images_video": 9, "images_gardees": 4}
    assert len(m["frames"]) == 4                     # 0..7 (la 9e = la 1re), une sur deux : 0, 2, 4, 6
    assert m["pixel_verif"]["ok"]


def test_boucle_ouverte_garde_la_derniere_et_une_sur_trois():
    noms = _film("pv_o", 9, fermee=False)
    _run({"source": {"kind": "images", "filenames": noms}, "cell": {"size": 128}, "boucle": {"une_sur": 3}},
         "cc000002")
    m = _manifest("cc000002")
    assert m["source"]["boucle"]["fermee"] is False and len(m["frames"]) == 3     # 0, 3, 6


def test_boucle_sonde_et_tir_comptent_pareil():
    noms = _film("pv_s", 9, fermee=True)
    r = _run({"source": {"kind": "images", "filenames": noms}, "boucle": {"une_sur": 2}, "extract_only": True},
             "cc000003")
    assert r["frames"] == 4


def test_boucle_options_gardees():
    from app.services import sprite_service as S
    assert S.normalize_opts({"boucle": True})["boucle"] == {"une_sur": 2}
    assert "boucle" not in S.normalize_opts({})
    for bad in ({"une_sur": 4}, {"une_sur": 0}, {"une_sur": "x"}, "oui"):
        with pytest.raises(ValueError):
            S.normalize_opts({"boucle": bad})


# ── les routes ───────────────────────────────────────────────────────────────────────────────────────────────
def _appel(methode, chemin, corps=None):
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.services.storage import init_db

    async def main():
        await init_db()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await (c.post(chemin, json=corps or {}) if methode == "POST" else c.get(chemin))
            j = None
            if r.status_code == 200 and isinstance(r.json(), dict) and "job_id" in r.json():
                j = (await c.get(f"/api/jobs/{r.json()['job_id']}")).json()
        return r, j
    return asyncio.run(main())


def test_routes_approuver_et_approbation():
    _run({"source": {"kind": "images", "filenames": [_sprite("pv_rt.png", 90)]}, "cell": {"size": 128},
          "pixel": {"target_px": 32, "palette": "gameboy"}}, "dd000001")
    r, _ = _appel("GET", "/api/assets/sprite/dd000001/approbation")
    assert r.status_code == 404
    r, _ = _appel("POST", "/api/assets/sprite/dd000001/approuver")
    assert r.status_code == 200 and r.json()["palette"] == "gameboy" and len(r.json()["palette_hex"]) == 4, r.text
    r, _ = _appel("GET", "/api/assets/sprite/dd000001/approbation")
    assert r.status_code == 200 and r.json()["target_px"] == 32
    r, _ = _appel("POST", "/api/assets/sprite/0badc0de/approuver")
    assert r.status_code == 404
    _run({"source": {"kind": "images", "filenames": ["pv_rt.png"]}, "cell": {"size": 128}}, "dd000002")
    r, _ = _appel("POST", "/api/assets/sprite/dd000002/approuver")
    assert r.status_code == 400
    r, _ = _appel("POST", "/api/assets/sprite", {"source": {"kind": "images", "filenames": ["pv_rt.png"]},
                                                 "pixel_verrou": "dd000002"})
    assert r.status_code == 400 and "not approved" in r.text


@pytest.fixture
def video(monkeypatch):
    """La vidéo SIMULÉE : pipeline.run enregistre la requête et ne part nulle part ; la clé fal « existe »."""
    from app.api import routes as R
    from app.config import settings
    appels, gardes = [], []

    async def faux_run(req, **kw):
        appels.append((req, kw))
        return kw.get("job_id")

    async def plafond(op, categorie, ref=None):
        gardes.append((op, categorie))
        return {}
    monkeypatch.setattr(R.pipeline, "run", faux_run)
    monkeypatch.setattr(R, "_plafond", plafond)
    monkeypatch.setattr(settings, "FAL_KEY", "cle-de-banc")
    return appels, gardes


def test_boucle_devis_ne_depense_rien(video):
    appels, gardes = video
    _sprite("pv_pose.png", 33)
    r, _ = _appel("POST", "/api/assets/sprite/boucle/devis", {"image_filename": "pv_pose.png", "duration_s": 5})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["usd"] > 0 and d["accepte_fin"] is True and d["une_sur"] == 2 and d["video_model"] == "seedance-2.5"
    assert d["cle_manquante"] is None and "op" not in d and "loop" in d["prompt_suffixe"]
    for corps in ({"image_filename": "../x.png"}, {"image_filename": "pv_pose.png", "une_sur": 5},
                  {"image_filename": "pv_pose.png", "duration_s": 30}, {"image_filename": "pv_pose.png",
                                                                        "video_model": "inconnu"}):
        r, _ = _appel("POST", "/api/assets/sprite/boucle/devis", corps)
        assert r.status_code == 400, (corps, r.text)
    r, _ = _appel("POST", "/api/assets/sprite/boucle/devis", {"image_filename": "absente.png"})
    assert r.status_code == 404
    assert appels == [] and gardes == []


def test_boucle_sans_cle_503_avant_tout(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "FAL_KEY", "")
    _sprite("pv_pose2.png", 33)
    r, _ = _appel("POST", "/api/assets/sprite/boucle", {"image_filename": "pv_pose2.png", "prompt": "walks",
                                                        "confirme_cout": True})
    assert r.status_code == 503, r.text
    r, _ = _appel("POST", "/api/assets/sprite/boucle/devis", {"image_filename": "pv_pose2.png"})
    assert r.json()["cle_manquante"] == "FAL_KEY"


def test_boucle_sans_confirmation_409_puis_confirmee_meme_pose_aux_deux_bouts(video):
    appels, gardes = video
    from app.services import sprite_service as S
    _sprite("pv_pose3.png", 33)
    r, _ = _appel("POST", "/api/assets/sprite/boucle", {"image_filename": "pv_pose3.png", "prompt": "walks"})
    assert r.status_code == 409 and r.json()["detail"]["usd"] > 0, r.text
    r, _ = _appel("POST", "/api/assets/sprite/boucle", {"image_filename": "pv_pose3.png", "prompt": "  ",
                                                        "confirme_cout": True})
    assert r.status_code == 400
    assert appels == [] and gardes == []
    r, j = _appel("POST", "/api/assets/sprite/boucle", {"image_filename": "pv_pose3.png", "prompt": "walks in place",
                                                        "confirme_cout": True, "une_sur": 3, "duration_s": 4})
    assert r.status_code == 200, r.text
    assert r.json()["devis"]["une_sur"] == 3 and r.json()["usd"] > 0
    assert j is not None and j["job_id"] == r.json()["job_id"]
    (req, kw), = appels
    assert kw["job_id"] == r.json()["job_id"]
    assert req.image_filename == "pv_pose3.png" and req.image_filename_end == "pv_pose3.png"
    assert req.custom_prompt.startswith("walks in place, ") and S.BOUCLE_SUFFIXE in req.custom_prompt
    assert req.voiceover_enabled is False and req.aspect_ratio.value == "1:1" and req.duration_s == 4
    assert [c for _op, c in gardes] == ["sprites"] and gardes[0][0]["kind"] == "seedance"


def test_boucle_refuse_un_modele_sans_image_de_fin(video):
    appels, gardes = video
    from app.services.fal_service import VIDEO_MODELS
    sans_fin = next(k for k, m in VIDEO_MODELS.items() if not m.get("end_image") and m.get("provider") != "google")
    _sprite("pv_pose4.png", 33)
    r, _ = _appel("POST", "/api/assets/sprite/boucle", {"image_filename": "pv_pose4.png", "prompt": "walks",
                                                        "video_model": sans_fin, "confirme_cout": True})
    assert r.status_code == 400, r.text
    assert appels == [] and gardes == []


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
