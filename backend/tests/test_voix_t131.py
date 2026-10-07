"""t131 (spec 2026-07-22-voiceover-quick-studio §9.1 et §9.3) — Voicebox dans Quick et le nœud Voiceover, ducking au
Render du Studio.

  [1] le fournisseur PAR GÉNÉRATION : /audio/voiceover porte `provider`, le service le suit (VP.resolve_provider(p)),
      la garde de dépense ne chiffre rien pour Voicebox même si le réglage global dit ElevenLabs ; un fournisseur
      demandé mais indisponible -> 409 (jamais un repli muet sur l'autre), inconnu -> 400.
  [2] le catalogue par fournisseur : /voices?provider=voicebox ; chaque profil Voicebox porte une préécoute
      (/api/voice/preview?voice_id=…&language=…).
  [3] la préécoute À LA DEMANDE + cache : générée une fois (audio/_previews/), servie ensuite sans régénérer ;
      id hors patron -> 400 ; Voicebox injoignable et rien en cache -> 503.
  [4] le ducking au Render : le duckDb de l'AudioMix devient un preset (léger / moyen / fort, ceux du Montage) ;
      mesuré au rendu ffmpeg : la « musique » (440 Hz) baisse sous la voix (1 kHz), pas ailleurs.
Run : & $PY tests/test_voix_t131.py   (depuis backend/)
"""
import asyncio, json, os, pathlib, re, shutil, subprocess, sys, tempfile

_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt131_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from app.config import settings                      # noqa: E402
settings.ELEVENLABS_API_KEY = ""
settings.VOICEBOX_URL = ""
# aucun appel ElevenLabs ne sort du banc : une régression qui y retomberait (mesuré sous mutation de generate_long)
# échoue ici au lieu de partir sur le réseau
import types                                         # noqa: E402
_faux11 = types.ModuleType("elevenlabs.client")


class _ElevenLabsInterdit:
    def __init__(self, *a, **k):
        raise RuntimeError("banc t131 : appel ElevenLabs interdit")


_faux11.ElevenLabs = _ElevenLabsInterdit
sys.modules["elevenlabs.client"] = _faux11
from app.services import voice_providers as VP       # noqa: E402
from app.services import elevenlabs_service as ES    # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


# ── bouchons : les deux fournisseurs « utilisables » selon ce que le banc décide, Voicebox écrit un vrai mp3 ──
DISPO = {"elevenlabs": True, "voicebox": True}
GLOBAL = {"v": "elevenlabs"}
APPELS = []


def faux_resolve(requested=None):
    req = (requested if requested is not None else GLOBAL["v"]) or ""
    if req in DISPO and DISPO[req]:
        return req
    for p in ("elevenlabs", "voicebox"):
        if DISPO[p]:
            return p
    return ""


FF = shutil.which("ffmpeg") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")


def faux_voicebox_tts(text, output_path, language="EN", voice_id=None, **kw):
    APPELS.append(("voicebox", text, language, voice_id))
    pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=f=300:d=0.4", str(output_path)], check=True)
    return pathlib.Path(output_path)


VP.resolve_provider = faux_resolve
VP.voicebox_tts = faux_voicebox_tts
VP.voicebox_reachable = lambda: DISPO["voicebox"]
VP.list_voicebox_voices = lambda timeout=10.0: VP.map_voicebox_profiles(
    [{"id": "p_fr1", "name": "Léa", "language": "fr", "preset_voice_id": "ff_siwis", "default_engine": "kokoro"}])

print("\n[1] le service suit le fournisseur demandé")
d = _tmp / "svc.mp3"
ES.VoiceoverService().generate(text="Bonjour", output_path=d, language="fr", voice_id="p_fr1", provider="voicebox")
check("1a_generate_provider_voicebox_passe_par_Voicebox_malgre_le_global_ElevenLabs",
      APPELS and APPELS[-1][0] == "voicebox" and APPELS[-1][3] == "p_fr1" and d.is_file(), APPELS[-1:])
n0 = len(APPELS)
ES.VoiceoverService().generate_long(text="Bonjour à tous.", output_path=_tmp / "long.mp3", language="fr", provider="voicebox")
check("1b_generate_long_transmet_le_fournisseur", len(APPELS) == n0 + 1 and APPELS[-1][0] == "voicebox")

from app.api import routes as R                      # noqa: E402
check("1c_garde_de_depense_Voicebox_rien_ElevenLabs_un_op",
      R._op_tts("bonjour", provider="voicebox") == [] and R._op_tts("bonjour", provider="elevenlabs") == [{"kind": "elevenlabs", "chars": 7}],
      (R._op_tts("bonjour", provider="voicebox"), R._op_tts("bonjour", provider="elevenlabs")))
check("1d_sans_fournisseur_le_global_comme_avant", R._op_tts("bonjour") == [{"kind": "elevenlabs", "chars": 7}])


async def scenario():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services.storage import init_db
    await init_db()
    R.VoiceoverService = ES.VoiceoverService
    ES.VoiceoverService.is_enabled = staticmethod(lambda: True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/audio/voiceover", json={"script": "Salut", "language": "fr", "voice_id": "p_fr1",
                                                        "provider": "voicebox", "name": "quick_vo"})
        j = r.json()
        check("1e_route_provider_voicebox_200_et_fichier", r.status_code == 200 and j.get("ok") and APPELS[-1][0] == "voicebox"
              and (settings.images_path.parent / "audio" / j["filename"]).is_file(), (r.status_code, j))
        DISPO["voicebox"] = False
        r = await c.post("/api/audio/voiceover", json={"script": "Salut", "provider": "voicebox"})
        check("1f_fournisseur_demande_indisponible_409_jamais_de_repli_muet", r.status_code == 409 and "Voicebox" in r.text, (r.status_code, r.text[:120]))
        DISPO["voicebox"] = True
        r = await c.post("/api/audio/voiceover", json={"script": "Salut", "provider": "openai"})
        check("1g_fournisseur_inconnu_400", r.status_code == 400, r.status_code)

        print("\n[2] catalogue par fournisseur")
        r = await c.get("/api/voices", params={"provider": "voicebox"})
        j = r.json()
        v = (j.get("voices") or [{}])[0]
        check("2a_voices_provider_voicebox", j.get("provider") == "voicebox" and v.get("voice_id") == "p_fr1", j)
        check("2b_chaque_profil_porte_sa_preecoute", v.get("preview_url") == "/api/voice/preview?voice_id=p_fr1&language=fr", v.get("preview_url"))
        r = await c.get("/api/voices", params={"provider": "zz"})
        check("2c_provider_inconnu_400", r.status_code == 400, r.status_code)
        # preuve 8799 : ElevenLabs choisi sans clé listait les profils Voicebox (resolve_provider se replie)
        DISPO["elevenlabs"] = False
        r = await c.get("/api/voices", params={"provider": "elevenlabs"})
        j = r.json()
        check("2d_fournisseur_nomme_indisponible_catalogue_vide_jamais_celui_de_l_autre",
              r.status_code == 200 and j.get("provider") == "elevenlabs" and j.get("voices") == [] and j.get("enabled") is False, j)
        DISPO["elevenlabs"] = True

        print("\n[3] préécoute à la demande + cache")
        n1 = len(APPELS)
        r1 = await c.get("/api/voice/preview", params={"voice_id": "p_fr1", "language": "fr"})
        cache = settings.images_path.parent / "audio" / "_previews" / "voicebox-p_fr1-fr.mp3"
        check("3a_premiere_ecoute_genere_et_sert_un_mp3", r1.status_code == 200 and r1.headers.get("content-type", "").startswith("audio/")
              and len(r1.content) > 500 and cache.is_file() and len(APPELS) == n1 + 1 and APPELS[-1][2].lower() == "fr",
              (r1.status_code, r1.headers.get("content-type"), len(APPELS) - n1, r1.text[:200]))
        r2 = await c.get("/api/voice/preview", params={"voice_id": "p_fr1", "language": "fr"})
        check("3b_seconde_ecoute_servie_du_cache_sans_regenerer", r2.status_code == 200 and r2.content == r1.content and len(APPELS) == n1 + 1)
        r = await c.get("/api/voice/preview", params={"voice_id": "../../x", "language": "fr"})
        check("3c_id_hors_patron_400", r.status_code == 400, r.status_code)
        DISPO["voicebox"] = False
        r = await c.get("/api/voice/preview", params={"voice_id": "p_autre", "language": "en"})
        check("3d_voicebox_injoignable_et_rien_en_cache_503", r.status_code == 503, r.status_code)
        r = await c.get("/api/voice/preview", params={"voice_id": "p_fr1", "language": "fr"})
        check("3e_le_cache_sert_meme_voicebox_eteint", r.status_code == 200 and r.content == r1.content, r.status_code)
        DISPO["voicebox"] = True
        r = await c.get("/api/audio")
        noms = json.dumps(r.json())
        check("3f_les_preecoutes_ne_polluent_pas_la_Library_audio", "voicebox-p_fr1" not in noms, noms[:200])

asyncio.run(scenario())

print("\n[4] ducking au Render")
from app.services import pipeline as PL                 # noqa: E402
check("4a_duckDb_vers_preset_leger_moyen_fort",
      PL._ducking_de({"file": "v.mp3", "duck_db": -3}) == {"threshold": 0.08, "ratio": 3.0, "attack": 50.0, "release": 400.0}
      and PL._ducking_de({"file": "v.mp3", "duck_db": -8}) == {"threshold": 0.05, "ratio": 6.0, "attack": 50.0, "release": 400.0}
      and PL._ducking_de({"file": "v.mp3", "duck_db": -14}) == {"threshold": 0.03, "ratio": 12.0, "attack": 50.0, "release": 400.0},
      [PL._ducking_de({"file": "v", "duck_db": x}) for x in (-3, -8, -14)])
check("4b_sans_duckDb_ou_illisible_pas_de_ducking", PL._ducking_de({"file": "v.mp3"}) is None and PL._ducking_de({"file": "v", "duck_db": "abc"}) is None
      and PL._ducking_de(None) is None and PL._ducking_de({"file": "v", "duck_db": 0}) is None)

T = pathlib.Path(tempfile.mkdtemp(prefix="dzt131_duck_"))
comp = T / "comp.mp4"
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:s=160x90:r=25:d=6", "-f", "lavfi", "-i", "sine=f=440:d=6",
                "-shortest", "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", str(comp)], check=True)
vo = T / "vo.wav"
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "aevalsrc='if(between(t,2,4),0.6*sin(2*PI*1000*t),0)':d=6:s=44100", str(vo)], check=True)


def bande(video, f, t0, t1):
    """RMS (dB) de la bande autour de f Hz entre t0 et t1."""
    r = subprocess.run([FF, "-v", "info", "-ss", str(t0), "-t", str(t1 - t0), "-i", str(video), "-vn",
                        "-af", f"bandpass=f={f}:width_type=h:w=60,bandpass=f={f}:width_type=h:w=60,astats=metadata=0:reset=0",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"RMS level dB:\s*(-?[\d.]+|-inf)", r.stderr)
    return float(m[-1]) if m and m[-1] != "-inf" else -200.0


plat = PL._apply_voiceover_post(comp, vo)
a_plat, b_plat = bande(plat, 440, 2.6, 3.6), bande(plat, 440, 0.5, 1.5)
plat2 = T / "plat.mp4"; shutil.copy(plat, plat2)
duck = PL._apply_voiceover_post(comp, vo, PL._ducking_de({"file": "vo", "duck_db": -14}))
a_duck, b_duck = bande(duck, 440, 2.6, 3.6), bande(duck, 440, 0.5, 1.5)
v_duck = bande(duck, 1000, 2.6, 3.6)
print(f"  440 Hz sous la voix : plat {a_plat:.1f} dB, ducké {a_duck:.1f} dB ; hors voix : plat {b_plat:.1f}, ducké {b_duck:.1f} ; voix {v_duck:.1f}")
check("4c_sous_la_voix_la_musique_baisse_d_au_moins_6_dB", a_plat - a_duck >= 6, (a_plat, a_duck))
check("4d_hors_de_la_voix_la_musique_reste_a_1_dB_pres", abs(b_plat - b_duck) <= 1.0, (b_plat, b_duck))
check("4e_la_voix_reste_presente", v_duck > -30, v_duck)
check("4f_sans_ducking_le_chemin_d_avant", plat.name.endswith("_vo.mp4"))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
