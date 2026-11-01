"""t406 (01/11/2026) — Gemini Omni Flash par la clé Google AI Studio (Interactions API) et retrait des Veo 3.1
preview de Google.

Doc officielle relue le 01/11/2026 (https://ai.google.dev/gemini-api/docs/omni, /api/interactions,
/docs/background-execution, /pricing) : POST /v1beta/interactions {model, input [image, image de fin?, texte],
response_format {type "video", aspect_ratio, resolution, duration, delivery}, generation_config.video_config.task,
background} -> {id, status} ; GET /v1beta/interactions/{id} jusqu'à un statut terminal ; la vidéo est dans
steps[type=model_output].content[type=video] (`data` base64 ou `uri` d'un fichier, prêt quand GET files/{id} rend
state ACTIVE). Veo 3.1 preview (les trois) arrêtés par Google le 22/10/2026.

AUCUN RÉSEAU : httpx.AsyncClient est remplacé par un client à httpx.MockTransport ; l'attente de sondage est nulle.
Style des bancs du dépôt : `check(label, cond, detail)`, ligne `=== N passed, M failed ===`, code de sortie.

Run: & $PY tests/test_google_omni_video.py   (depuis backend/)
"""
import asyncio
import base64
import inspect
import json
import os
import pathlib
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
_tmp = tempfile.mkdtemp(prefix="omni_google_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp          # jamais le .env de l'utilisateur
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ.pop("GEMINI_API_KEY", None)
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import httpx                                                        # noqa: E402
from loguru import logger                                           # noqa: E402

from app.config import settings                                     # noqa: E402
from app.services import google_video as GV                         # noqa: E402
from app.services import pricing                                    # noqa: E402
from app.services.fal_service import VIDEO_MODELS, refus_retire, est_retire, resolve_video_model  # noqa: E402

ok = fail = 0
CLE = "cle-factice-AIzaTEST-0123456789"       # ne doit JAMAIS sortir dans un journal, une URL ou une erreur


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


journal: list[str] = []
logger.add(lambda m: journal.append(str(m)), level="DEBUG")


# ── faux Google : chaque test pose sa liste de réponses, le transport enregistre les requêtes ────────────────────
class FauxGoogle:
    def __init__(self, reponses):
        self.reponses = list(reponses)    # (méthode, fragment d'URL, code, corps json | octets)
        self.requetes: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requetes.append(request)
        for i, (meth, frag, code, corps) in enumerate(self.reponses):
            if request.method == meth and frag in str(request.url):
                self.reponses.pop(i)
                if isinstance(corps, (bytes, bytearray)):
                    return httpx.Response(code, content=bytes(corps))
                return httpx.Response(code, json=corps)
        return httpx.Response(599, json={"error": {"message": f"inattendu {request.method} {request.url.path}"}})


_vrai_client = httpx.AsyncClient


def brancher(faux: FauxGoogle):
    def fabrique(*a, **kw):
        kw.pop("verify", None)
        return _vrai_client(*a, transport=httpx.MockTransport(faux), **kw)
    GV.httpx.AsyncClient = fabrique


async def _pas_d_attente(_s):
    return None

GV.asyncio.sleep = _pas_d_attente
settings.GEMINI_API_KEY = CLE

png = pathlib.Path(_tmp, "images", "debut.png"); png.write_bytes(b"\x89PNG_debut")
jpg = pathlib.Path(_tmp, "images", "fin.jpg"); jpg.write_bytes(b"\xff\xd8_fin")
MP4 = b"\x00\x00\x00\x20ftypisom-faux-mp4"


def corps_post(faux) -> dict:
    return json.loads(next(r for r in faux.requetes if r.method == "POST").content)


def run(coro):
    try:
        return asyncio.run(coro), None
    except Exception as e:  # noqa: BLE001
        return None, e


# ── registre ─────────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[registre]")
m = VIDEO_MODELS.get("gemini-omni-flash-google") or {}
check("entree_presente", bool(m))
check("voie_google_famille_omni", m.get("provider") == "google" and m.get("family") == "gemini_omni", repr(m))
check("endpoint_omni_11", m.get("endpoint") == "gemini-omni-1.1-flash", repr(m.get("endpoint")))
check("caps_comme_le_jumeau_fal", m.get("durations") == list(range(3, 11)) and m.get("ratios") == ["9:16", "16:9"]
      and m.get("resolutions") == ["720p", "1080p"] and m.get("end_image") is True and m.get("seed") is False, repr(m))
check("omni_pas_retire", not est_retire(m))
for vid in ("veo-3.1-google", "veo-3.1-fast-google", "veo-3.1-lite-google"):
    v = VIDEO_MODELS.get(vid) or {}
    check(f"{vid}_retire_le_22_10", v.get("retire") == "2026-10-22" and est_retire(v), repr(v.get("retire")))
    check(f"{vid}_remplacant_omni", v.get("remplacant") == "gemini-omni-flash-google", repr(v.get("remplacant")))
    check(f"{vid}_reste_resoluble", resolve_video_model(vid)["id"] == vid)
r_fr = refus_retire(resolve_video_model("veo-3.1-google"), "fr")
r_en = refus_retire(resolve_video_model("veo-3.1-google"), "en")
check("refus_retire_fr", "Veo 3.1 (Google)" in r_fr and "Gemini Omni Flash (Google)" in r_fr
      and "22/10/2026" in r_fr and "rien n'a été lancé" in r_fr, r_fr)
check("refus_retire_en", "Veo 3.1 (Google)" in r_en and "Gemini Omni Flash (Google)" in r_en
      and "nothing was started" in r_en, r_en)
for fal_id in ("veo-3.1-fal", "veo-3.1-fast-fal", "veo-3.1-lite-fal", "gemini-omni-flash"):
    check(f"{fal_id}_pas_retire", not est_retire(VIDEO_MODELS[fal_id]))

# ── corps de la requête Interactions ────────────────────────────────────────────────────────────────────────────
print("\n[corps]")
b = GV.build_interactions_body(prompt="un chat court", image_path=png, end_image_path=None, duration=4,
                               aspect_ratio="16:9", resolution="720p", model="gemini-omni-1.1-flash")
check("modele", b.get("model") == "gemini-omni-1.1-flash")
check("tache_i2v", b.get("generation_config") == {"video_config": {"task": "image_to_video"}}, repr(b.get("generation_config")))
check("arriere_plan", b.get("background") is True)
check("format_video", b.get("response_format") == {"type": "video", "aspect_ratio": "16:9", "resolution": "720p",
                                                     "duration": "4s", "delivery": "uri"}, repr(b.get("response_format")))
inp = b.get("input") or []
check("entree_image_puis_texte", [p.get("type") for p in inp] == ["image", "text"], repr([p.get("type") for p in inp]))
check("image_base64_mime", inp and inp[0].get("mime_type") == "image/png"
      and base64.b64decode(inp[0].get("data", "")) == png.read_bytes())
check("texte_prompt", inp and inp[-1].get("text") == "un chat court")
b2 = GV.build_interactions_body(prompt="p", image_path=png, end_image_path=jpg, duration=8,
                                aspect_ratio="1:1", resolution="8k", model="gemini-omni-1.1-flash")
inp2 = b2.get("input") or []
check("debut_puis_fin_puis_texte", [p.get("type") for p in inp2] == ["image", "image", "text"]
      and base64.b64decode(inp2[1]["data"]) == jpg.read_bytes() and inp2[1]["mime_type"] == "image/jpeg", repr(inp2))
check("ratio_inconnu_vertical", b2["response_format"]["aspect_ratio"] == "9:16")
check("resolution_hors_registre_720p", b2["response_format"]["resolution"] == "720p")
check("duree_8s", b2["response_format"]["duration"] == "8s")
check("aucun_negatif", "negative" not in json.dumps(b2).lower())
check("1080p_passe", GV.build_interactions_body(prompt="p", image_path=png, end_image_path=None, duration=4,
                                                 aspect_ratio="16:9", resolution="1080p",
                                                 model="gemini-omni-1.1-flash")["response_format"]["resolution"] == "1080p")
check("voie_interactions", GV.est_interactions("gemini-omni-1.1-flash") and not GV.est_interactions("veo-3.1-generate-preview"))

# ── parcours : création en arrière-plan, sondage, vidéo inline ──────────────────────────────────────────────────
print("\n[parcours inline]")
termine = {"id": "v1_abc", "status": "completed", "model": "gemini-omni-1.1-flash", "object": "interaction",
           "usage": {"total_output_tokens": 23168},
           "steps": [{"type": "user_input", "content": [{"type": "text", "text": "p"}]},
                     {"type": "thought", "content": [{"type": "thought", "text": "..."}]},
                     {"type": "model_output", "content": [{"type": "video", "mime_type": "video/mp4",
                                                          "data": base64.b64encode(MP4).decode()}]}]}
faux = FauxGoogle([("POST", "/v1beta/interactions", 200, {"id": "v1_abc", "status": "in_progress"}),
                   ("GET", "/v1beta/interactions/v1_abc", 200, {"id": "v1_abc", "status": "in_progress"}),
                   ("GET", "/v1beta/interactions/v1_abc", 200, termine)])
brancher(faux)
res, err = run(GV.GoogleVeoClient.generate_video(image_path=png, end_image_path=jpg, prompt="p", negative_prompt="flou",
                                                  duration=4, aspect_ratio="16:9", resolution="720p",
                                                  model="gemini-omni-1.1-flash"))
check("pas_d_erreur", err is None, repr(err))
url = GV.GoogleVeoClient.extract_video_url(res or {})
check("url_courte_inline", isinstance(url, str) and url.startswith("google-inline:") and len(url) < 80, repr(url)[:120])
check("usage_rendu", (res or {}).get("usage") == {"total_output_tokens": 23168}, repr((res or {}).get("usage")))
check("trois_appels", [r.method for r in faux.requetes] == ["POST", "GET", "GET"], repr([r.method for r in faux.requetes]))
check("cle_en_entete", all(r.headers.get("x-goog-api-key") == CLE for r in faux.requetes))
check("cle_jamais_dans_l_url", all(CLE not in str(r.url) for r in faux.requetes))
check("deux_images_envoyees", [p["type"] for p in corps_post(faux)["input"]] == ["image", "image", "text"])
dest = pathlib.Path(_tmp, "out", "inline.mp4")
_r, err = run(GV.GoogleVeoClient.download_video(url, dest))
check("mp4_ecrit", err is None and dest.read_bytes() == MP4, repr(err))
_r, err = run(GV.GoogleVeoClient.download_video(url, pathlib.Path(_tmp, "out", "bis.mp4")))
check("inline_consomme_une_fois", isinstance(err, RuntimeError) and str(err).startswith("google:"), repr(err))

# ── parcours : création déjà terminée, livraison par URI (fichier à attendre) ────────────────────────────────────
print("\n[parcours uri]")
uri = "https://generativelanguage.googleapis.com/v1beta/files/abc-123:download?alt=media"
termine_uri = {"id": "v1_u", "status": "completed",
               "steps": [{"type": "model_output", "content": [{"type": "video", "mime_type": "video/mp4", "uri": uri}]}]}
faux = FauxGoogle([("POST", "/v1beta/interactions", 200, termine_uri),
                   ("GET", "/v1beta/files/abc-123", 200, {"name": "files/abc-123", "state": "PROCESSING"}),
                   ("GET", "/v1beta/files/abc-123", 200, {"name": "files/abc-123", "state": "ACTIVE"}),
                   ("GET", "/v1beta/files/abc-123:download", 200, MP4)])
brancher(faux)
res, err = run(GV.GoogleVeoClient.generate_video(image_path=png, prompt="p", duration=4, aspect_ratio="16:9",
                                                  resolution="720p", model="gemini-omni-1.1-flash"))
check("uri_rendue", err is None and GV.GoogleVeoClient.extract_video_url(res or {}) == uri, repr(err or res))
check("fichier_attendu_actif", [r.url.path for r in faux.requetes if r.method == "GET"]
      == ["/v1beta/files/abc-123", "/v1beta/files/abc-123"], repr([r.url.path for r in faux.requetes]))
dest = pathlib.Path(_tmp, "out", "uri.mp4")
_r, err = run(GV.GoogleVeoClient.download_video(uri, dest))
check("mp4_uri_ecrit", err is None and dest.read_bytes() == MP4, repr(err))
check("uri_cle_en_entete_pas_en_url", all(r.headers.get("x-goog-api-key") == CLE and CLE not in str(r.url)
                                          for r in faux.requetes))
faux = FauxGoogle([("POST", "/v1beta/interactions", 200, termine_uri),
                   ("GET", "/v1beta/files/abc-123", 200, {"state": "FAILED"})])
brancher(faux)
_r, err = run(GV.GoogleVeoClient.generate_video(image_path=png, prompt="p", duration=4, aspect_ratio="16:9",
                                                 resolution="720p", model="gemini-omni-1.1-flash"))
check("fichier_failed_erreur", isinstance(err, RuntimeError) and "FAILED" in str(err), repr(err))

# ── échecs ──────────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[echecs]")
for statut in ("failed", "cancelled", "incomplete"):
    faux = FauxGoogle([("POST", "/v1beta/interactions", 200, {"id": "v1_f", "status": "in_progress"}),
                       ("GET", "/v1beta/interactions/v1_f", 200,
                        {"id": "v1_f", "status": statut, "error": {"code": 400, "message": "bloqué par la sécurité"}})])
    brancher(faux)
    _r, err = run(GV.GoogleVeoClient.generate_video(image_path=png, prompt="p", duration=4, aspect_ratio="16:9",
                                                     resolution="720p", model="gemini-omni-1.1-flash"))
    check(f"statut_{statut}_erreur_claire", isinstance(err, RuntimeError) and str(err).startswith("google:")
          and statut in str(err) and "bloqué par la sécurité" in str(err), repr(err))
faux = FauxGoogle([("POST", "/v1beta/interactions", 404,
                    {"error": {"code": 404, "message": "models/gemini-omni-1.1-flash is not found"}})])
brancher(faux)
_r, err = run(GV.GoogleVeoClient.generate_video(image_path=png, prompt="p", duration=4, aspect_ratio="16:9",
                                                 resolution="720p", model="gemini-omni-1.1-flash"))
check("http_404_erreur_claire", isinstance(err, RuntimeError) and "HTTP 404" in str(err) and "not found" in str(err), repr(err))
faux = FauxGoogle([("POST", "/v1beta/interactions", 200, {"id": "v1_v", "status": "completed",
                                                           "steps": [{"type": "model_output", "content": []}]})])
brancher(faux)
_r, err = run(GV.GoogleVeoClient.generate_video(image_path=png, prompt="p", duration=4, aspect_ratio="16:9",
                                                 resolution="720p", model="gemini-omni-1.1-flash"))
check("termine_sans_video_erreur", isinstance(err, RuntimeError) and "no video" in str(err), repr(err))
_ancien = GV._POLL_TIMEOUT_S
GV._POLL_TIMEOUT_S = 10.0
faux = FauxGoogle([("POST", "/v1beta/interactions", 200, {"id": "v1_t", "status": "in_progress"})]
                  + [("GET", "/v1beta/interactions/v1_t", 200, {"id": "v1_t", "status": "in_progress"})] * 5)
brancher(faux)
_r, err = run(GV.GoogleVeoClient.generate_video(image_path=png, prompt="p", duration=4, aspect_ratio="16:9",
                                                 resolution="720p", model="gemini-omni-1.1-flash"))
GV._POLL_TIMEOUT_S = _ancien
check("delai_depasse_erreur", isinstance(err, RuntimeError) and "timed out" in str(err) and "v1_t" in str(err), repr(err))
check("cle_jamais_journalisee", not any(CLE in ligne for ligne in journal), "la clé est sortie dans le journal")

# ── tarif et garde de coût ──────────────────────────────────────────────────────────────────────────────────────
print("\n[tarif]")
p = pricing.load()
check("tarif_720p", pricing.video_rate("gemini-omni-flash-google", "720p", p) == 0.11)
check("tarif_1080p", pricing.video_rate("gemini-omni-flash-google", "1080p", p) == 0.15)
ligne = pricing.estimate({"kind": "seedance", "duration_s": 4, "model": "gemini-omni-flash-google",
                          "resolution": "720p"}, p)["breakdown"][0]
check("devis_4s_720p", ligne.get("provider") == "google" and abs(ligne.get("usd", -1) - 0.44) < 1e-6
      and "Gemini Omni Flash (Google)" in ligne.get("label", ""), repr(ligne))
from fastapi import HTTPException                                   # noqa: E402
from app.api import routes                                          # noqa: E402
from app.models.schemas import GenerateRequest                      # noqa: E402
req = GenerateRequest(image_filename="debut.png", custom_prompt="p", video_model="gemini-omni-flash-google",
                      duration_s=4, resolution="720p", max_usd=0.30)
try:
    routes._garde_cout([routes._devis_video(req)], req.max_usd)
    code = None
except HTTPException as e:
    code = e.status_code
check("max_usd_bas_refuse_402", code == 402, repr(code))
req_ok = GenerateRequest(image_filename="debut.png", custom_prompt="p", video_model="gemini-omni-flash-google",
                         duration_s=4, resolution="720p", max_usd=0.50)
try:
    total = routes._garde_cout([routes._devis_video(req_ok)], req_ok.max_usd)
except HTTPException as e:
    total = e
check("max_usd_suffisant_passe", total == 0.44 or (isinstance(total, float) and abs(total - 0.44) < 1e-6), repr(total))

# ── routes : refus du retiré, listes ────────────────────────────────────────────────────────────────────────────
print("\n[routes]")
for vid in ("veo-3.1-google", "veo-3.1-fast-google", "veo-3.1-lite-google"):
    try:
        routes._cle_video_ou_503(vid)
        e_ = None
    except HTTPException as e:
        e_ = e
    check(f"{vid}_refuse_410", e_ is not None and e_.status_code == 410 and "Gemini Omni Flash (Google)" in str(e_.detail),
          repr(e_ and (e_.status_code, e_.detail)))
settings.GEMINI_API_KEY = ""
try:
    routes._cle_video_ou_503("gemini-omni-flash-google")
    e_ = None
except HTTPException as e:
    e_ = e
check("omni_google_sans_cle_503", e_ is not None and e_.status_code == 503 and "GEMINI_API_KEY" in str(e_.detail),
      repr(e_ and e_.detail))
out = asyncio.run(routes.list_video_models())
by = {x["id"]: x for x in out.get("models") or []}
check("liste_sans_les_retires", not ({"veo-3.1-google", "veo-3.1-fast-google", "veo-3.1-lite-google"} & set(by)), sorted(by))
check("liste_omni_google_indispo_sans_cle", (by.get("gemini-omni-flash-google") or {}).get("available") is False)
settings.GEMINI_API_KEY = CLE
out = asyncio.run(routes.list_video_models())
by = {x["id"]: x for x in out.get("models") or []}
og = by.get("gemini-omni-flash-google") or {}
check("liste_omni_google_dispo_avec_cle", og.get("available") is True and og.get("voie") == "gemini"
      and og.get("cle") == "GEMINI_API_KEY" and og.get("fl") is True, repr(og))
check("liste_prix_omni_google", (og.get("usd_per_s") or {}).get("720p") == 0.11, repr(og.get("usd_per_s")))
check("jumeaux_omni", og.get("jumeau") == "gemini-omni-flash"
      and (by.get("gemini-omni-flash") or {}).get("jumeau") == "gemini-omni-flash-google", repr(og.get("jumeau")))
check("veo_fal_sans_jumeau_retire", all((by.get(f) or {}).get("jumeau") is None
                                         for f in ("veo-3.1-fal", "veo-3.1-fast-fal", "veo-3.1-lite-fal")),
      repr({f: (by.get(f) or {}).get("jumeau") for f in ("veo-3.1-fal", "veo-3.1-fast-fal", "veo-3.1-lite-fal")}))
from app.services import catalogue_ia as CI                         # noqa: E402
i2v = {x["id"]: x for x in CI._videos(False)}
fl = {x["id"] for x in CI._videos(True)}
check("catalogue_sans_retires", not ({"veo-3.1-google", "veo-3.1-fast-google", "veo-3.1-lite-google"} & set(i2v)))
check("catalogue_omni_google", (i2v.get("gemini-omni-flash-google") or {}).get("voie") == "gemini"
      and "gemini-omni-flash-google" in fl, repr(i2v.get("gemini-omni-flash-google")))
from app.services.fal_service import refus_fin                       # noqa: E402
check("refus_fin_liste_omni_google", "Gemini Omni Flash (Google)" in refus_fin("PixVerse v6", "fr"))

# ── pipeline : l'image de fin part vers Google, le retiré est refusé avant tout appel ─────────────────────────────
print("\n[pipeline]")
from app.services import pipeline as PL                             # noqa: E402
src = inspect.getsource(PL.Pipeline.run)
check("pipeline_passe_la_fin_a_google", "end_image_path=end_image_path" in src)
check("pipeline_refuse_le_retire", "refus_retire(" in src)

# ── i18n ────────────────────────────────────────────────────────────────────────────────────────────────────────
print("\n[i18n]")
msgs = json.loads(pathlib.Path(__file__).resolve().parents[1].joinpath("app", "i18n", "messages.json")
                  .read_text(encoding="utf-8"))
e = msgs.get("ia.video.retire") or {}
check("cle_i18n_fr_en", bool(e.get("fr")) and bool(e.get("en")) and "{remplacant}" in e["fr"] and "{remplacant}" in e["en"], repr(e))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
