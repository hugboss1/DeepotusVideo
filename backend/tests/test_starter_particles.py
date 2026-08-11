"""Recette — catalogue de démarrage CC0, particules locales, musique fal.

Lancé avec le python embarqué de l'app et DEEPOTUS_DATA_DIR isolé :

  runtime\\python\\python.exe -m pytest backend/tests/test_starter_particles.py -v

Ce que ces tests protègent, dans l'ordre d'importance :

1. La LICENCE. Le catalogue est redistribué dans l'installeur ; si une source
   cesse d'être CC0 et que personne ne s'en aperçoit, on livre des octets qu'on
   n'a pas le droit de vendre. Le test échoue sur toute source non-CC0.
2. L'INTÉGRITÉ du catalogue : tout fichier déclaré existe, aucun identifiant en
   double. Une entrée fantôme = une tuile cassée dans l'UI.
3. La frame 0 NON VIDE de chaque preset. Un sprite dont la première image est
   transparente s'affiche comme une vignette noire partout dans l'app — le
   défaut est invisible en test unitaire et criant à l'écran.
4. Les GARDES d'entrée (bornes, couleurs, presets inconnus) et le confinement
   des chemins d'assets.
5. Le contrat des modèles de musique : un réglage non supporté par un modèle
   ne doit JAMAIS partir dans la charge utile fal (422 illisible), et doit être
   remonté à l'utilisateur.
"""
import json

import pytest
from PIL import Image

from app.services import music_service as MS
from app.services import particle_service as PS
from app.services import starter_catalog as SC


# ── catalogue ───────────────────────────────────────────────────────────────

def test_catalogue_present_et_non_vide():
    cat = SC.load()
    assert cat.get("available") is True, (
        "catalogue absent — lancer scripts/build_starter_catalog.py --fetch")
    assert len(cat["particles"]) >= 60
    assert len(cat["sfx"]) >= 400
    assert len(cat["anims"]) >= 4


def test_toutes_les_sources_sont_cc0():
    """Garde-fou de redistribution : une seule source non-CC0 rend
    l'installeur non livrable."""
    for s in SC.load()["sources"]:
        assert s["license"] == "CC0-1.0", (
            f"source non redistribuable : {s['id']} ({s['license']})")


def test_chaque_fichier_declare_existe():
    cat = SC.load()
    for item in cat["particles"] + cat["sfx"]:
        for key in ("file", "thumb"):
            rel = item.get(key)
            if rel:
                assert (SC.STARTER_DIR / rel).is_file(), f"{item['id']}: {rel}"
    for anim in cat["anims"]:
        assert len(SC.anim_frames(anim["id"])) == anim["frames"]


def test_identifiants_uniques():
    cat = SC.load()
    for key in ("particles", "sfx", "anims"):
        ids = [i["id"] for i in cat[key]]
        assert len(ids) == len(set(ids)), f"doublons dans {key}"


def test_familles_exhaustives():
    """Un son sans famille est livré dans l'installeur et invisible dans
    l'UI — le pire des deux coûts."""
    cat = SC.load()
    connues = {f["id"] for f in cat["sfx_families"]}
    orphelins = [s["id"] for s in cat["sfx"] if s["family"] not in connues]
    assert not orphelins, f"sons sans famille : {orphelins[:5]}"


def test_durees_renseignees():
    """Les durées sont lues au build (en-tête Ogg) : le runtime ne doit
    jamais avoir à lancer ffprobe pour afficher la liste."""
    durs = [s["dur"] for s in SC.load()["sfx"]]
    assert all(d > 0 for d in durs)
    assert max(durs) < 60


def test_recherche_bilingue():
    """L'utilisateur ne sait pas si le catalogue est en français ou en
    anglais : « verre » et « glass » doivent tomber sur les mêmes sons."""
    fr = {i["id"] for i in SC.browse("sfx", query="verre")}
    en = {i["id"] for i in SC.browse("sfx", query="glass")}
    assert fr and fr == en


def test_asset_path_confine_au_catalogue():
    with pytest.raises(SC.StarterError) as e:
        SC.asset_path("particle", "../../config")
    assert e.value.status in (400, 404)


def test_kind_inconnu_rejete():
    with pytest.raises(SC.StarterError):
        SC.browse("nawak")


# ── particules ──────────────────────────────────────────────────────────────

def test_presets_pointent_sur_des_textures_reelles():
    ids = {p["id"] for p in SC.load()["particles"]}
    for p in PS.PRESETS:
        assert p["texture"] in ids, f"{p['id']}: texture {p['texture']} absente"


def test_presets_normalisables():
    for p in PS.PRESETS:
        o = PS.normalize_opts({"preset": p["id"]})
        assert o["emitter"]["frames"] >= 2
        assert o["emitter"]["blend"] in ("add", "normal")
        assert o["emitter"]["orient"] in PS._ORIENTS


@pytest.mark.parametrize("preset", [p["id"] for p in PS.PRESETS])
def test_frame_zero_non_vide(preset, tmp_path):
    """Défaut vu à l'écran, invisible autrement : une première image
    transparente donne une vignette noire dans toutes les grilles."""
    o = PS.normalize_opts({"preset": preset, "seed": 11})
    tex = SC.asset_path("particle", o["texture"])
    frames = PS.render_frames(tex, o, tmp_path / preset)
    assert len(frames) == o["emitter"]["frames"]
    with Image.open(frames[0]) as im:
        assert im.convert("RGBA").getbbox() is not None, (
            f"{preset}: frame 0 entièrement transparente")


def test_rendu_deterministe(tmp_path):
    """Même graine, même image : sans ça, « régénérer » n'a pas de sens."""
    o = PS.normalize_opts({"preset": "goldburst", "seed": 42})
    tex = SC.asset_path("particle", o["texture"])
    a = PS.render_frames(tex, o, tmp_path / "a")[3].read_bytes()
    b = PS.render_frames(tex, o, tmp_path / "b")[3].read_bytes()
    assert a == b


def test_boucle_stream_raccorde(tmp_path):
    """En mode « stream » le temps est cyclique : la dernière image doit
    ressembler à la première, sinon le « alpha · boucle » est un mensonge."""
    o = PS.normalize_opts({"preset": "ashes", "seed": 5})
    tex = SC.asset_path("particle", o["texture"])
    fr = PS.render_frames(tex, o, tmp_path / "loop")
    with Image.open(fr[0]) as f0, Image.open(fr[-1]) as fl:
        a0 = f0.convert("RGBA").getchannel("A")
        al = fl.convert("RGBA").getchannel("A")
        m0 = sum(i * v for i, v in enumerate(a0.histogram()))
        ml = sum(i * v for i, v in enumerate(al.histogram()))
    assert m0 > 0 and ml > 0
    assert abs(m0 - ml) / max(m0, ml) < 0.45, "raccord de boucle trop brutal"


@pytest.mark.parametrize("bad,motif", [
    ({"preset": "nexistepas"}, "preset"),
    ({"preset": "explosion", "emitter": {"count": 9999}}, "count"),
    ({"preset": "explosion", "emitter": {"frames": 1}}, "frames"),
    ({"preset": "explosion", "emitter": {"color0": "zzz"}}, "couleur"),
    ({"preset": "explosion", "emitter": {"blend": "multiply"}}, "blend"),
    ({"preset": "explosion", "emitter": {"orient": "nope"}}, "orient"),
    ({"preset": "explosion", "emitter": {"size": 777}}, "size"),
    ({}, "texture"),
])
def test_entrees_invalides_rejetees(bad, motif):
    with pytest.raises(ValueError) as e:
        PS.normalize_opts(bad)
    assert motif in str(e.value).lower()


def test_reglage_inconnu_ignore_sans_planter():
    o = PS.normalize_opts({"preset": "explosion", "emitter": {"zorglub": 3}})
    assert "zorglub" not in o["emitter"]


# ── musique ─────────────────────────────────────────────────────────────────

def test_catalogue_musique_complet():
    c = MS.catalog()
    assert c["default"] in {m["id"] for m in c["models"]}
    assert len(c["moods"]) >= 6
    for m in c["models"]:
        assert m["usd"] > 0 and m["desc"]


def test_prompt_combine_ambiance_et_texte():
    p = MS.build_prompt("une guitare sèche", "lofi")
    assert p.startswith(MS.MOOD_BY_ID["lofi"]["prompt"])
    assert "guitare" in p


def test_prompt_vide_rejete():
    with pytest.raises(MS.MusicError):
        MS.build_prompt("", "")


def test_reglage_non_supporte_jamais_envoye_et_signale():
    """Lyria impose sa durée et ne prend pas de paroles. Les envoyer quand
    même produirait une 422 fal illisible ; les taire silencieusement ferait
    croire à l'utilisateur qu'elles ont été prises en compte."""
    args, notes = MS._payload(MS.MUSIC_MODELS["lyria3"], "x",
                              {"duration_s": 90, "lyrics": "abc", "seed": 3})
    assert set(args) == {"prompt"}
    assert len(notes) == 3


def test_duree_routee_sur_le_bon_champ():
    a, _ = MS._payload(MS.MUSIC_MODELS["stable-audio-25"], "x",
                       {"duration_s": 90})
    assert a["seconds_total"] == 90
    a, _ = MS._payload(MS.MUSIC_MODELS["cassetteai"], "x", {"duration_s": 90})
    assert a["duration"] == 90


def test_duree_hors_bornes_rejetee():
    with pytest.raises(MS.MusicError):
        MS._payload(MS.MUSIC_MODELS["stable-audio-25"], "x",
                    {"duration_s": 9999})


def test_paroles_coupent_l_instrumental():
    a, _ = MS._payload(MS.MUSIC_MODELS["minimax-music-26"], "x",
                       {"lyrics": "[Verse]\nsalut"})
    assert a["is_instrumental"] is False and a["lyrics"]


def test_voix_sans_paroles_active_l_ecriture_auto():
    a, _ = MS._payload(MS.MUSIC_MODELS["minimax-music-26"], "x",
                       {"instrumental": False})
    assert a["is_instrumental"] is False and a.get("lyrics_optimizer") is True


@pytest.mark.parametrize("res,attendu", [
    ({"audio": {"url": "http://x/a.mp3"}}, "http://x/a.mp3"),
    ({"audio_file": {"url": "http://x/b.wav"}}, "http://x/b.wav"),
    ({"audio": "http://x/c.mp3"}, "http://x/c.mp3"),
])
def test_url_audio_trouvee_quel_que_soit_le_schema(res, attendu):
    """Les schémas de sortie fal ne sont pas homogènes d'une famille de
    modèles à l'autre — on cherche, on ne suppose pas."""
    assert MS._audio_url(res) == attendu


def test_reponse_sans_audio_leve_une_erreur_lisible():
    with pytest.raises(MS.MusicError) as e:
        MS._audio_url({"status": "ok"})
    assert "fal.ai" in e.value.message


# ── cohérence build / runtime ───────────────────────────────────────────────

def test_catalog_json_est_bien_forme():
    data = json.loads((SC.STARTER_DIR / "catalog.json").read_text("utf-8"))
    assert data["version"] == 1
    assert (SC.STARTER_DIR / "NOTICE.txt").is_file(), (
        "NOTICE.txt manquant — les attributions doivent être livrées")
