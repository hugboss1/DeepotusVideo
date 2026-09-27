"""Tâche 5 du plan retours-ia (F) — Seedance 2.5 par défaut, estimation
juste et GARDE DE COÛT serveur.

Ce que le banc tient :
  [0] état vide : aucun `pricing.json` -> les défauts, dont les deux clés
      neuves `video_max_usd_per_request` (10 $) et `video_max_gen_s` (10 s) ;
  [1] `DEFAULT_VIDEO_MODEL == "seedance-2.5"` et `/video-models` le dit ;
  [2] `pricing.estimate` : un modèle vide ou absent se résout au tarif 2.5
      (720p -> 0,473 $/s), JAMAIS au 0,04 hérité ; même règle pour
      l'estimation épisodes (`seedance_s`) et le plan marketing ; l'ancien
      tarif n'est plus atteint que par le drapeau explicite `legacy` (le coût
      HISTORIQUE des jobs d'avant la colonne `video_model`) ;
  [3] la durée GÉNÉRÉE est plafonnée à `video_max_gen_s` (natif du modèle) ;
  [4] la garde : 402 sur `/generate`, `/generate/batch`,
      `/generate/composition` et le rendu de layout, avec un détail qui
      nomme les montants ; ZÉRO appel à `FalSeedanceClient.generate_video`
      en cas de refus, un appel espionné (sans réseau) en cas d'accord ;
  [5] le pipeline envoie la durée plafonnée et prolonge le reste (ffmpeg,
      espionné) ; l'ancien défaut `seedance-v1-pro` reste choisissable ;
  [6] une soumission fal par clip : l'application ne rejoue JAMAIS (ni
      avant ni après acceptation) — un ReadTimeout arrive après l'envoi, et
      fal_client rejoue déjà en interne (risque résiduel daté) ;
  [7] revue du 27/09 : HeyGen compte dans la garde, id inconnu -> 400,
      valeurs non finies, max_usd des slots, coût des jobs sur la durée
      générée, « -0,00 ».

AUCUN appel fal réel : `FalSeedanceClient.{upload_image,generate_video,
download_video}` sont des espions, et `fal_client.{submit_async,
subscribe_async,run_async,upload_file_async}` sont remplacés par des gardes
qui comptent — leur compteur doit rester à ZÉRO hors de la section [6], où
ils sont des faux explicites.

Run: & $PY tests/test_seedance_garde.py   (un processus, depuis backend/)
"""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="sdgarde_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ["FAL_KEY"] = "test-key"
os.environ["HEYGEN_API_KEY"] = "test-heygen"
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY",
           "ANTHROPIC_API_KEY"):
    os.environ.pop(_k, None)
Path(TMP, "images").mkdir(parents=True, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import fal_client                                                # noqa: E402
import httpx                                                     # noqa: E402
from httpx import AsyncClient, ASGITransport                     # noqa: E402

from app.config import settings                                  # noqa: E402

settings.ELEVENLABS_API_KEY = ""   # aucune voix synthétisée, quoi qu'il arrive
settings.FAL_KEY = "test-key"
settings.HEYGEN_API_KEY = "test-heygen"

from app.main import app                                         # noqa: E402
from app.services import fal_service as FS                       # noqa: E402
from app.services import pricing as P                            # noqa: E402
from app.services.fal_service import FalSeedanceClient           # noqa: E402
from app.services.storage import init_db                         # noqa: E402
from app.api import routes as R                                  # noqa: E402

ok = fail = 0
_plantages = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def temoin(e):
    """TEMOIN d'un appel qui a LEVE — numéroté et distinguable."""
    global _plantages
    _plantages += 1
    return "%s: %s ·ECHEC#%d" % (type(e).__name__, e, _plantages)


# ── gardes réseau fal : tout appel est COMPTÉ et refusé ─────────────────────
RESEAU = {"n": 0, "noms": []}


def _garde(nom):
    async def _refus(*a, **k):
        RESEAU["n"] += 1
        RESEAU["noms"].append(nom)
        raise RuntimeError(f"GARDE RESEAU : {nom} appelé dans un banc")
    return _refus


for _nom in ("submit_async", "subscribe_async", "run_async",
             "upload_file_async", "upload_async", "upload_image_async"):
    setattr(fal_client, _nom, _garde(_nom))

# ── espions sur le client Seedance ──────────────────────────────────────────
ESPION = {"gen": [], "upload": 0, "download": 0, "extend": []}
_VRAI_GENERATE = FalSeedanceClient.__dict__["generate_video"]


class ArretBanc(Exception):
    pass


async def _esp_upload(image_path):
    ESPION["upload"] += 1
    return "https://fake.invalid/" + Path(image_path).name


async def _esp_generate(**kw):
    ESPION["gen"].append(kw)
    return {"video": {"url": "https://fake.invalid/v.mp4"}, "seed": 1}


async def _esp_download(video_url, dest_path):
    ESPION["download"] += 1
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    Path(dest_path).write_bytes(b"")
    return Path(dest_path)


FalSeedanceClient.upload_image = staticmethod(_esp_upload)
FalSeedanceClient.generate_video = staticmethod(_esp_generate)
FalSeedanceClient.download_video = staticmethod(_esp_download)


def _esp_extend(src, dest, target, mode):
    ESPION["extend"].append({"target": target, "mode": mode})
    raise ArretBanc("arrêt du pipeline après la prolongation (banc)")


R.pipeline.merger.extend = _esp_extend

# composition et layout : l'orchestration aval (HeyGen, ffmpeg) est espionnée
AVAL = {"composition": 0, "layout": 0}


async def _esp_compo(request):
    AVAL["composition"] += 1
    return ("c", "s", "h")


async def _esp_layout(**kw):
    AVAL["layout"] += 1
    return "j"


R.pipeline.run_composition = _esp_compo
R.pipeline.render_template = _esp_layout

IMG = "depart.png"
Path(TMP, "images", IMG).write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)

asyncio.run(init_db())


def reset():
    ESPION["gen"].clear()
    ESPION["upload"] = 0
    ESPION["download"] = 0
    ESPION["extend"].clear()
    AVAL["composition"] = 0
    AVAL["layout"] = 0


async def _post(path, body):
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://t") as c:
        # json.dumps du stdlib (NaN/Infinity permis) : un client peut les
        # envoyer, httpx `json=` les refuserait avant la route
        return await c.post("/api" + path, content=json.dumps(body),
                            headers={"content-type": "application/json"})


def post(path, body):
    """(status, detail|json) — un appel qui lève rend un témoin, jamais {}."""
    try:
        r = asyncio.run(_post(path, body))
        try:
            js = r.json()
        except Exception:
            js = {"_texte": r.text}
        return r.status_code, js
    except Exception as e:  # noqa: BLE001
        return -1, {"_temoin": temoin(e)}


def gen_body(**kw):
    b = {"image_filename": IMG, "custom_prompt": "un chat",
         "voiceover_enabled": False, "duration_s": 10}
    b.update(kw)
    return b


PRICING_FILE = Path(TMP) / "pricing.json"

# ── [0] état vide ───────────────────────────────────────────────────────────
print("\n[0] état vide : pas de pricing.json -> les défauts.")
check("etat_vide_aucun_pricing_json", not PRICING_FILE.exists(), str(PRICING_FILE))
_p = P.load()
check("defaut_plafond_requete_10",
      _p.get("video_max_usd_per_request") == 10.0,
      repr(_p.get("video_max_usd_per_request")))
check("defaut_duree_generee_10", _p.get("video_max_gen_s") == 10,
      repr(_p.get("video_max_gen_s")))
check("cles_neuves_dans_DEFAULTS_donc_sauvegardables",
      "video_max_usd_per_request" in P.DEFAULTS and "video_max_gen_s" in P.DEFAULTS,
      repr(sorted(P.DEFAULTS)))

# ── [1] le défaut ───────────────────────────────────────────────────────────
print("\n[1] Seedance 2.5 est le défaut.")
check("defaut_seedance_25", FS.DEFAULT_VIDEO_MODEL == "seedance-2.5",
      repr(FS.DEFAULT_VIDEO_MODEL))
check("resolve_vide_donne_25",
      FS.resolve_video_model(None)["id"] == "seedance-2.5"
      and FS.resolve_video_model("")["id"] == "seedance-2.5",
      repr(FS.resolve_video_model(None)["id"]))
try:
    _vm = asyncio.run(R.list_video_models())
except Exception as e:  # noqa: BLE001
    _vm = {"_temoin": temoin(e)}
check("video_models_annonce_25", _vm.get("default") == "seedance-2.5", repr(_vm.get("default")))
check("ancien_defaut_toujours_au_registre",
      "seedance-v1-pro" in FS.VIDEO_MODELS
      and any(m.get("id") == "seedance-v1-pro" for m in (_vm.get("models") or [])),
      repr(sorted(FS.VIDEO_MODELS)))
check("generate_video_defaut_signature_25",
      _VRAI_GENERATE.__func__.__defaults__[-1] == "seedance-2.5"
      if hasattr(_VRAI_GENERATE, "__func__") else False,
      repr(getattr(getattr(_VRAI_GENERATE, "__func__", None), "__defaults__", None)))

# ── [2] l'estimation ────────────────────────────────────────────────────────
print("\n[2] estimation : un modèle vide se résout au tarif 2.5.")


def _tot(op):
    try:
        return P.estimate(op, P.load())["total_usd"]
    except Exception as e:  # noqa: BLE001
        return temoin(e)


_e720 = _tot({"kind": "seedance", "duration_s": 10, "resolution": "720p"})
check("vide_720p_10s_vaut_4_73", _e720 == 4.73, repr(_e720))
_evide = _tot({"kind": "seedance", "duration_s": 10, "model": "", "resolution": "720p"})
check("modele_chaine_vide_vaut_4_73", _evide == 4.73, repr(_evide))
_esans = _tot({"kind": "seedance", "duration_s": 10})
# 1080p demandé à un modèle sans 1080p -> sa colonne max (720p)
check("sans_resolution_vaut_4_73_jamais_0_40", _esans == 4.73 and _esans != 0.4,
      repr(_esans))
_e480 = _tot({"kind": "seedance", "duration_s": 10, "resolution": "480p"})
check("vide_480p_vaut_2_205", _e480 == 2.205, repr(_e480))
# témoin positif : un modèle nommé garde SON tarif
_ev1 = _tot({"kind": "seedance", "duration_s": 10, "model": "seedance-v1-pro",
             "resolution": "720p"})
check("temoin_v1_pro_garde_son_tarif", _ev1 == 0.54, repr(_ev1))
try:
    _lbl = P.estimate({"kind": "seedance", "duration_s": 5}, P.load())["breakdown"][0]["label"]
except Exception as e:  # noqa: BLE001
    _lbl = temoin(e)
check("ligne_vide_porte_le_libelle_25", "Seedance 2.5" in str(_lbl), repr(_lbl))
# l'ancien tarif n'est plus atteint que par le drapeau explicite (historique)
_leg = _tot({"kind": "seedance", "duration_s": 10, "legacy": True})
_leg_attendu = round(10 * P.load()["seedance_usd_per_s"], 4)
check("legacy_explicite_garde_l_ancien_tarif", _leg == _leg_attendu, f"{_leg} vs {_leg_attendu}")
_ep = _tot({"kind": "episode", "images": 0, "chars": 0, "seedance_s": 10})
check("episode_seedance_s_au_tarif_25", _ep == 4.73, repr(_ep))
_mk = _tot({"kind": "marketing_plan", "posts": 1})
_mk_attendu = round(0.003 + 4.73, 4)
check("plan_marketing_un_post_image_plus_10s_25", _mk == _mk_attendu, f"{_mk} vs {_mk_attendu}")

# ── [3] durée générée plafonnée ─────────────────────────────────────────────
print("\n[3] la durée générée est plafonnée à video_max_gen_s.")


def _gd(mid, req, cap):
    try:
        return FS.generated_duration(FS.resolve_video_model(mid), req, cap)
    except Exception as e:  # noqa: BLE001
        return temoin(e)


check("25_20s_genere_10", _gd("seedance-2.5", 20, 10) == 10, repr(_gd("seedance-2.5", 20, 10)))
check("25_3s_genere_4_natif_min", _gd("seedance-2.5", 3, 10) == 4, repr(_gd("seedance-2.5", 3, 10)))
check("25_plafond_6", _gd("seedance-2.5", 20, 6) == 6, repr(_gd("seedance-2.5", 20, 6)))
check("v1_60s_genere_10", _gd("seedance-v1-pro", 60, 10) == 10, repr(_gd("seedance-v1-pro", 60, 10)))
check("veo_plafond_5_redescend_au_natif_4", _gd("veo-3.1-fast-fal", 8, 5) == 4,
      repr(_gd("veo-3.1-fast-fal", 8, 5)))
check("sans_plafond_comportement_d_avant", _gd("seedance-2.5", 20, None) == 20,
      repr(_gd("seedance-2.5", 20, None)))
try:
    _gs = P.video_gen_seconds("seedance-2.5", 20, P.load())
except Exception as e:  # noqa: BLE001
    _gs = temoin(e)
check("pricing_secondes_generees_lit_le_plafond", _gs == 10, repr(_gs))
try:
    _msg = P.cost_guard(4.73, 1.0, P.load())
except Exception as e:  # noqa: BLE001
    _msg = temoin(e)
check("garde_message_nomme_les_montants",
      isinstance(_msg, str) and "Estimation 4,73 $ > plafond 1,00 $" in _msg, repr(_msg))
try:
    _ok_msg = P.cost_guard(4.73, None, P.load())
except Exception as e:  # noqa: BLE001
    _ok_msg = temoin(e)
check("garde_sans_max_usd_4_73_passe_sous_10", _ok_msg is None, repr(_ok_msg))

# ── [4] la garde sur les routes ─────────────────────────────────────────────
print("\n[4] la garde : 402 et zéro génération, ou accord et un appel espionné.")

reset()
_s, _j = post("/generate", gen_body(max_usd=1.0, resolution="720p"))
_det = str(_j.get("detail", _j))
check("generate_max_usd_1_refuse_402", _s == 402, f"{_s} {_j}")
check("generate_402_nomme_estimation_et_plafond",
      "Estimation 4,73 $ > plafond 1,00 $" in _det, repr(_det))
check("generate_refus_zero_appel_fal", len(ESPION["gen"]) == 0 and ESPION["upload"] == 0,
      repr(ESPION))

reset()
_s, _j = post("/generate", gen_body(resolution="720p"))
check("quick_10s_720p_sans_max_usd_passe", _s == 200, f"{_s} {_j}")
check("quick_accord_un_appel_espionne", len(ESPION["gen"]) == 1, repr(ESPION["gen"]))
_g = ESPION["gen"][0] if ESPION["gen"] else {}
check("quick_accord_modele_25", _g.get("model_id") == "seedance-2.5", repr(_g))
check("quick_accord_duree_10", _g.get("duration") == 10, repr(_g))

reset()
_s, _j = post("/generate", gen_body(max_usd=5.0))   # 1080p demandé -> 720p facturé
check("generate_max_usd_5_passe_4_73", _s == 200 and len(ESPION["gen"]) == 1, f"{_s} {_j} {ESPION['gen']}")

# plafond serveur modifié par pricing.json
PRICING_FILE.write_text(json.dumps({"video_max_usd_per_request": 3.0}), encoding="utf-8")
reset()
_s, _j = post("/generate", gen_body(resolution="720p"))
_det = str(_j.get("detail", _j))
check("plafond_serveur_3_refuse_sans_max_usd", _s == 402 and len(ESPION["gen"]) == 0,
      f"{_s} {_j}")
check("plafond_serveur_nomme", "Estimation 4,73 $ > plafond 3,00 $" in _det, repr(_det))
reset()
# max_usd PLUS HAUT que le plafond serveur ne le lève pas
_s, _j = post("/generate", gen_body(resolution="720p", max_usd=50.0))
check("max_usd_ne_leve_pas_le_plafond_serveur", _s == 402 and len(ESPION["gen"]) == 0,
      f"{_s} {_j}")
PRICING_FILE.unlink()

# lot : la somme des variations
reset()
_s, _j = post("/generate/batch", gen_body(duration_s=5, variations_count=8))
_det = str(_j.get("detail", _j))
check("lot_x8_5s_refuse_18_92", _s == 402 and "Estimation 18,92 $ > plafond 10,00 $" in _det,
      f"{_s} {_det}")
check("lot_refus_zero_appel", len(ESPION["gen"]) == 0, repr(ESPION["gen"]))
reset()
_s, _j = post("/generate/batch", gen_body(duration_s=10, variations_count=2))
check("lot_x2_10s_9_46_passe", _s == 200 and len(ESPION["gen"]) == 2, f"{_s} {_j} {len(ESPION['gen'])}")
reset()
_s, _j = post("/generate/batch", gen_body(duration_s=10, variations_count=2, max_usd=9.0))
check("lot_x2_max_usd_9_refuse", _s == 402 and len(ESPION["gen"]) == 0, f"{_s} {_j}")

# composition
HG = {"avatar_id": "a", "voice_id": "v", "script": "Bonjour " * 30}
reset()
_s, _j = post("/generate/composition", {"seedance": gen_body(resolution="720p"),
                                        "heygen": HG, "max_usd": 1.0})
_det = str(_j.get("detail", _j))
check("composition_max_usd_refuse_402", _s == 402 and AVAL["composition"] == 0, f"{_s} {_j}")
check("composition_402_nomme_le_montant", "Estimation 4," in _det and "plafond 1,00 $" in _det,
      repr(_det))
reset()
_s, _j = post("/generate/composition", {"seedance": gen_body(resolution="720p"), "heygen": HG})
check("composition_sous_plafond_passe", _s == 200 and AVAL["composition"] == 1, f"{_s} {_j}")
reset()
_s, _j = post("/generate/composition", {"seedance": gen_body(resolution="720p", max_usd=1.0),
                                        "heygen": HG})
check("composition_max_usd_du_cote_seedance_compte", _s == 402 and AVAL["composition"] == 0,
      f"{_s} {_j}")

# layout
try:
    _tid = R.template_engine.list_templates()[0]["id"]
except Exception as e:  # noqa: BLE001
    _tid = temoin(e)
_slot = {"source_kind": "seedance", "seedance": gen_body(resolution="720p")}
reset()
_s, _j = post(f"/layout-templates/{_tid}/render",
              {"template_id": _tid, "slot_values": {"a": _slot, "b": _slot, "c": _slot}})
_det = str(_j.get("detail", _j))
check("layout_trois_slots_14_19_refuse", _s == 402 and "Estimation 14,19 $ > plafond 10,00 $" in _det
      and AVAL["layout"] == 0, f"{_s} {_det}")
reset()
_s, _j = post(f"/layout-templates/{_tid}/render",
              {"template_id": _tid, "slot_values": {"a": _slot}})
check("layout_un_slot_passe", _s == 200 and AVAL["layout"] == 1, f"{_s} {_j}")
reset()
_s, _j = post(f"/layout-templates/{_tid}/render",
              {"template_id": _tid, "slot_values": {"a": _slot, "b": _slot, "c": _slot},
               "preview": True})
check("layout_apercu_ne_coute_rien_donc_pas_de_garde", _s == 200 and AVAL["layout"] == 1,
      f"{_s} {_j}")
reset()
_s, _j = post(f"/layout-templates/{_tid}/render",
              {"template_id": _tid, "slot_values": {"a": _slot}, "max_usd": 2.0})
check("layout_max_usd_refuse", _s == 402 and AVAL["layout"] == 0, f"{_s} {_j}")

# ── [5] le pipeline ─────────────────────────────────────────────────────────
print("\n[5] pipeline : durée envoyée plafonnée, le reste prolongé par ffmpeg.")
reset()
_s, _j = post("/generate", gen_body(duration_s=20, resolution="720p",
                                    video_model="seedance-2.5"))
_g = ESPION["gen"][0] if ESPION["gen"] else {}
check("pipeline_20s_envoie_10_a_fal", _s == 200 and _g.get("duration") == 10, f"{_s} {_g}")
check("pipeline_prolonge_a_20_par_ffmpeg",
      [x.get("target") for x in ESPION["extend"]] == [20], repr(ESPION["extend"]))
reset()
_s, _j = post("/generate", gen_body(duration_s=10, video_model="seedance-v1-pro"))
_g = ESPION["gen"][0] if ESPION["gen"] else {}
check("ancien_defaut_choisissable", _s == 200 and _g.get("model_id") == "seedance-v1-pro",
      f"{_s} {_g}")
check("temoin_10s_pas_de_prolongation", ESPION["extend"] == [], repr(ESPION["extend"]))

# ── [6] une seule soumission par clip ────────────────────────────────────────
print("\n[6] soumission fal : jamais de rejeu par l'application.")
# Revue du 27/09 : ReadTimeout/ReadError/RemoteProtocolError sont des
# TransportError survenues APRES l'envoi — les rejouer refacture. Et
# fal_client rejoue DEJA en interne (MAX_ATTEMPTS=10) : la boucle
# exterieure est supprimee, `submit_async` est appele UNE fois.
FAUX = {"submit": 0, "get": 0}


class _Handle:
    request_id = "req-banc"

    def __init__(self, get_leve):
        self._leve = get_leve

    async def iter_events(self, with_logs=False, interval=0.1):
        if False:
            yield None

    async def get(self, interval=0.1):
        FAUX["get"] += 1
        if self._leve:
            raise RuntimeError("boom apres acceptation")
        return {"video": {"url": "https://fake.invalid/ok.mp4"}}


def _faux_submit(echecs, get_leve, exc=None):
    async def _submit(application, arguments, **kw):
        FAUX["submit"] += 1
        if FAUX["submit"] <= echecs:
            raise exc
        return _Handle(get_leve)
    return _submit


def _appel_reel():
    fn = _VRAI_GENERATE.__func__ if hasattr(_VRAI_GENERATE, "__func__") else _VRAI_GENERATE
    return asyncio.run(fn(image_url="https://fake.invalid/i.png", prompt="p",
                          duration=10, resolution="720p", model_id="seedance-2.5"))


def _essai(echecs, get_leve, exc=None):
    FAUX.update(submit=0, get=0)
    fal_client.submit_async = _faux_submit(echecs, get_leve, exc)
    try:
        r = _appel_reel()
        return r, "aucune erreur"
    except Exception as e:  # noqa: BLE001
        return None, str(e)


_sauve_submit = fal_client.submit_async
_sauve_subscribe = fal_client.subscribe_async
_req = httpx.Request("POST", "https://queue.fal.invalid/x")
try:
    _r, _e = _essai(0, False)
    check("temoin_soumission_nominale_un_submit_un_get",
          FAUX["submit"] == 1 and FAUX["get"] == 1
          and ((_r or {}).get("video") or {}).get("url") == "https://fake.invalid/ok.mp4",
          f"{FAUX} {_r} {_e}")
    for _cls in (httpx.ReadTimeout, httpx.ReadError, httpx.RemoteProtocolError,
                 httpx.ConnectError, httpx.ConnectTimeout):
        _r, _e = _essai(1, False, _cls("coupure (banc)", request=_req))
        check(f"{_cls.__name__}_au_1er_essai_une_seule_soumission",
              FAUX["submit"] == 1 and FAUX["get"] == 0 and _e.startswith("fal.ai:"),
              f"{FAUX} {_e}")
    _r, _e = _essai(0, True)
    check("erreur_apres_acceptation_ne_resoumet_pas",
          FAUX["submit"] == 1 and FAUX["get"] == 1, f"{FAUX} {_e}")
    check("erreur_apres_acceptation_prefixee_fal", _e.startswith("fal.ai:"), repr(_e))
    _r, _e = _essai(1, False, ValueError("422 schema"))
    check("refus_non_transport_n_est_pas_rejoue", FAUX["submit"] == 1, f"{FAUX} {_e}")
    check("subscribe_n_est_plus_utilise", RESEAU["noms"].count("subscribe_async") == 0,
          repr(RESEAU["noms"]))
finally:
    fal_client.submit_async = _sauve_submit
    fal_client.subscribe_async = _sauve_subscribe

# ── [7] corrections de la revue du 27/09 ────────────────────────────────────
print("\n[7] HeyGen compte, id inconnu, valeurs non finies, slots, coût des jobs.")
import math                                                      # noqa: E402,F401
from types import SimpleNamespace                                # noqa: E402

# (a) HeyGen compte : Seedance seul (4,73) passe sous 4,80, Seedance + HeyGen
# (300 caractères ≈ 0,085 $) le dépasse.
HG300 = {"avatar_id": "a", "voice_id": "v", "script": "x" * 300}
_hg_usd = P.estimate({"kind": "heygen", "chars": 300}, P.load())["total_usd"]
check("temoin_heygen_300_car_coute_plus_de_7_cents", _hg_usd > 0.07, repr(_hg_usd))
reset()
_s, _j = post("/generate", gen_body(resolution="720p", max_usd=4.80))
check("temoin_seedance_seul_passe_sous_4_80", _s == 200, f"{_s} {_j}")
reset()
_s, _j = post("/generate/composition", {"seedance": gen_body(resolution="720p"),
                                        "heygen": HG300, "max_usd": 4.80})
check("composition_heygen_fait_depasser_402", _s == 402 and AVAL["composition"] == 0
      and len(ESPION["gen"]) == 0, f"{_s} {_j}")
_slot = {"source_kind": "seedance", "seedance": gen_body(resolution="720p")}
_slot_hg = {"source_kind": "heygen", "heygen": HG300}
reset()
_s, _j = post(f"/layout-templates/{_tid}/render",
              {"template_id": _tid, "slot_values": {"a": _slot}, "max_usd": 4.80})
check("temoin_layout_seedance_seul_passe_sous_4_80", _s == 200 and AVAL["layout"] == 1,
      f"{_s} {_j}")
reset()
_s, _j = post(f"/layout-templates/{_tid}/render",
              {"template_id": _tid, "slot_values": {"a": _slot, "h": _slot_hg},
               "max_usd": 4.80})
check("layout_heygen_fait_depasser_402", _s == 402 and AVAL["layout"] == 0
      and len(ESPION["gen"]) == 0, f"{_s} {_j}")

# (b) id de modèle inconnu -> 400 qui liste les ids, sur les quatre routes
_nope = gen_body(video_model="nope")
for _nom, _path, _body in (
        ("generate", "/generate", _nope),
        ("batch", "/generate/batch", {**_nope, "variations_count": 2}),
        ("composition", "/generate/composition", {"seedance": _nope, "heygen": HG300}),
        ("layout", f"/layout-templates/{_tid}/render",
         {"template_id": _tid, "slot_values": {"a": {"source_kind": "seedance",
                                                     "seedance": _nope}}})):
    reset()
    _s, _j = post(_path, _body)
    _det = str(_j.get("detail", _j))
    check(f"modele_inconnu_400_liste_{_nom}",
          _s == 400 and "nope" in _det and "seedance-2.5" in _det
          and len(ESPION["gen"]) == 0 and AVAL["composition"] == 0 and AVAL["layout"] == 0,
          f"{_s} {_det}")

# (c) valeurs non finies ou négatives venues de pricing.json ou du client
_lot3 = gen_body(resolution="720p", variations_count=3)   # 14,19 $ > 10
for _nom, _texte in (("nan", '{"video_max_usd_per_request": NaN}'),
                     ("inf", '{"video_max_usd_per_request": Infinity}'),
                     ("negatif", '{"video_max_usd_per_request": -5}')):
    PRICING_FILE.write_text(_texte, encoding="utf-8")
    reset()
    _s, _j = post("/generate/batch", _lot3)
    _det = str(_j.get("detail", _j))
    check(f"plafond_{_nom}_retombe_a_10", _s == 402 and "plafond 10,00 $" in _det
          and len(ESPION["gen"]) == 0, f"{_s} {_det}")
PRICING_FILE.write_text('{"video_max_usd_per_request": 0}', encoding="utf-8")
reset()
_s, _j = post("/generate/batch", {**_lot3, "variations_count": 3})
check("temoin_plafond_0_veut_dire_aucun", _s == 200 and len(ESPION["gen"]) == 3, f"{_s} {_j}")
_tarifs = dict(P.DEFAULTS["video_usd_per_s"])
_tarifs["seedance-2.5"] = {"480p": 0.2205, "720p": float("nan")}
PRICING_FILE.write_text(json.dumps({"video_usd_per_s": _tarifs}), encoding="utf-8")
reset()
_s, _j = post("/generate", gen_body(resolution="720p", max_usd=50))
_det = str(_j.get("detail", _j))
check("tarif_nan_total_non_fini_refuse", _s == 402 and len(ESPION["gen"]) == 0, f"{_s} {_det}")
for _nom, _texte in (("nan", '{"video_max_gen_s": NaN}'),
                     ("inf", '{"video_max_gen_s": Infinity}'),
                     ("negatif", '{"video_max_gen_s": -4}')):
    PRICING_FILE.write_text(_texte, encoding="utf-8")
    try:
        _gs = P.video_gen_seconds("seedance-2.5", 20, P.load())
    except Exception as e:  # noqa: BLE001
        _gs = temoin(e)
    check(f"duree_generee_{_nom}_retombe_a_10", _gs == 10, repr(_gs))
PRICING_FILE.unlink()
reset()
_s, _j = post("/generate", gen_body(resolution="720p", max_usd=float("nan")))
check("max_usd_nan_client_422", _s == 422 and len(ESPION["gen"]) == 0, f"{_s} {_j}")
reset()
_s, _j = post("/generate", gen_body(resolution="720p", max_usd=float("inf")))
check("max_usd_inf_client_422", _s == 422 and len(ESPION["gen"]) == 0, f"{_s} {_j}")
reset()
_s, _j = post("/generate", gen_body(resolution="720p", max_usd=-1))
check("max_usd_negatif_client_422", _s == 422 and len(ESPION["gen"]) == 0, f"{_s} {_j}")
reset()
_s, _j = post("/generate/composition", {"seedance": gen_body(resolution="720p",
                                                             max_usd=float("nan")),
                                        "heygen": HG300})
check("max_usd_nan_cote_seedance_422", _s == 422 and AVAL["composition"] == 0, f"{_s} {_j}")

# (d) layout : le max_usd de chaque slot compte (le plus bas gagne)
_slot_max = {"source_kind": "seedance", "seedance": gen_body(resolution="720p", max_usd=1.0)}
reset()
_s, _j = post(f"/layout-templates/{_tid}/render",
              {"template_id": _tid, "slot_values": {"a": _slot_max}})
_det = str(_j.get("detail", _j))
check("layout_max_usd_du_slot_compte", _s == 402 and "plafond 1,00 $" in _det
      and AVAL["layout"] == 0, f"{_s} {_det}")
reset()
_s, _j = post(f"/layout-templates/{_tid}/render",
              {"template_id": _tid, "slot_values": {"a": _slot_max}, "max_usd": 0.5})
_det = str(_j.get("detail", _j))
check("layout_le_plus_bas_gagne", _s == 402 and "plafond 0,50 $" in _det, f"{_s} {_det}")

# (e) coût des jobs : durée GÉNÉRÉE pour un job avec modèle, legacy inchangé
_p = P.load()


def _jc(**kw):
    job = SimpleNamespace(provider="seedance", cost_meta=None, **kw)
    try:
        return R._job_to_cost(job, _p)["total_usd"]
    except Exception as e:  # noqa: BLE001
        return temoin(e)


_v = _jc(duration_s=20, video_model="seedance-2.5")
_attendu = round(P.DEFAULTS["flux_image_usd"] + 10 * 0.473, 4)
check("job_25_20s_facture_10s_generees", _v == _attendu, f"{_v} vs {_attendu}")
_v = _jc(duration_s=20, video_model=None)
_attendu = round(P.DEFAULTS["flux_image_usd"] + 20 * P.DEFAULTS["seedance_usd_per_s"], 4)
check("job_legacy_20s_inchange", _v == _attendu, f"{_v} vs {_attendu}")
_v = _jc(duration_s=60, video_model=None)
_attendu = round(P.DEFAULTS["flux_image_usd"] + 60 * P.DEFAULTS["seedance_usd_per_s"], 4)
check("job_legacy_60s_inchange_pas_de_plafond", _v == _attendu, f"{_v} vs {_attendu}")
_v = _jc(duration_s=5, video_model="veo-3.1-fast-fal")
_attendu = round(P.DEFAULTS["flux_image_usd"] + 6 * 0.1, 4)   # 5 s -> 6 s natives
check("job_veo_5s_facture_6s_natives", _v == _attendu, f"{_v} vs {_attendu}")
_v = _jc(duration_s=5, video_model="modele-retire")
check("job_modele_retire_ne_plante_pas", isinstance(_v, float), repr(_v))

# (f) -0.0 s'affiche « 0,00 »
_m0, _m1 = P._usd_fr(-0.0), P._usd_fr(-0.001)
check("usd_fr_moins_zero", _m0 == "0,00" and _m1 == "0,00", f"{_m0!r} {_m1!r}")
_t = P._usd_fr(4.73)
check("temoin_usd_fr", _t == "4,73", repr(_t))

# ── garde réseau et plantages ───────────────────────────────────────────────
check("aucun_appel_reseau_fal", RESEAU["n"] == 0, repr(RESEAU["noms"]))
check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont levé — voir les lignes FAIL ci-dessus")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
