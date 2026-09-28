# -*- coding: utf-8 -*-
"""MIGRATION HEYGEN v1/v2 -> v3 (28/09/2026, suivi des chantiers #1).

HeyGen retire ses endpoints v1/v2 le 1er novembre 2026 (developers.heygen.com,
« Endpoint Version Comparison »). Le chemin par defaut de l'application
passait encore par /v2/video/generate, /v1/video_status.get, /v2/avatars,
/v2/voices, /v2/user/remaining_quota et l'upload v1 des talking photos.

CORRESPONDANCE (doc officielle) :
  generation        POST /v3/videos (type avatar)
  statut            GET  /v3/videos/{id}         -> {data:{status, video_url, failure_message}}
  avatars           GET  /v3/avatars/looks       -> {data:[...], has_more, next_token}
  un look           GET  /v3/avatars/looks/{id}  -> supported_api_engines, status
  voix              GET  /v3/voices              -> {data:[...], has_more, next_token}
  compte / quota    GET  /v3/users/me            -> wallet | subscription | usage_based
  avatar photo      POST /v3/avatars (type photo, file base64) puis statut du look
DECISIONS (utilisateur, 28/09) : moteur par defaut Avatar III (comme la v2),
resolu PAR LOOK (premier moteur supporte sinon) ; pauses SSML converties en
ponctuation (la v3 ne documente pas le SSML).

METHODE : faux transport httpx (aucun appel reseau) qui repond comme la doc
v3 et consigne chaque requete. TEMOIN : le heygen_service.py de e88e4cc (git
show) appelle encore /v2/voices. Regle des assertions negatives : chaque
« absent » a son temoin positif. Faute n6 : details par _d().
Run : & $PY tests/test_heygen_v3_migration.py   (depuis backend/)
"""
import asyncio, base64, importlib.util, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzhg3_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["HEYGEN_API_KEY"] = "test-heygen-key"
os.environ.setdefault("FAL_KEY", "test-key")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                  # noqa: E402
logger.remove()
import httpx                                               # noqa: E402
from app.services import heygen_service as HS              # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:500]
    except Exception as e:                                   # pragma: no cover
        return f"(detail illisible : {e})"


# ── faux HeyGen v3 ───────────────────────────────────────────────────────────
REQ = []           # (methode, hote, chemin, params, corps json ou None)
ETAT = {"billing": "subscription", "polls": {}}
LOOKS_ENGINES = {"look_iii": ["avatar_v", "avatar_iv", "avatar_iii"],
                 "look_iv_only": ["avatar_v", "avatar_iv"],
                 "lk_new": ["avatar_iv"]}


def _look(i, own="public", typ="studio_avatar", status="completed"):
    return {"id": i, "name": f"Look {i}", "avatar_type": typ, "group_id": f"ag_{i}",
            "preview_image_url": f"https://img/{i}.png", "preview_video_url": None,
            "gender": "female", "tags": [], "default_voice_id": "vc_default",
            "supported_api_engines": LOOKS_ENGINES.get(i, ["avatar_iv", "avatar_iii"]),
            "image_width": 1080, "image_height": 1920, "preferred_orientation": "portrait",
            "status": status, "error": None}


def handler(request: httpx.Request) -> httpx.Response:
    p = request.url.path
    q = dict(request.url.params)
    body = None
    if request.content:
        try:
            body = json.loads(request.content)
        except Exception:
            body = "<binaire>"
    REQ.append((request.method, request.url.host, p, q, body))
    J = lambda o, s=200: httpx.Response(s, json=o)
    if request.method == "GET" and p == "/v3/voices":
        if q.get("type") == "private":
            return J({"data": [{"voice_id": "vc_mine", "name": "Ma voix", "language": "French",
                                "gender": "male", "preview_audio_url": "https://a/mine.mp3",
                                "support_pause": True, "support_locale": False, "type": "private"}],
                      "has_more": False, "next_token": None})
        if not q.get("token"):
            return J({"data": [{"voice_id": "vc_1", "name": "Asha", "language": "English", "gender": "female",
                                "preview_audio_url": "https://a/1.mp3", "support_pause": True,
                                "support_locale": True, "type": "public"}],
                      "has_more": True, "next_token": "p2"})
        return J({"data": [{"voice_id": "vc_2", "name": "Bruno", "language": "French", "gender": "male",
                            "preview_audio_url": None, "support_pause": False, "support_locale": False,
                            "type": "public"}], "has_more": False, "next_token": None})
    if request.method == "GET" and p == "/v3/avatars/looks":
        if q.get("ownership") == "private":
            return J({"data": [_look("lk_mine", "private", "photo_avatar")], "has_more": False, "next_token": None})
        if not q.get("token"):
            return J({"data": [_look("look_iii")], "has_more": True, "next_token": "t2"})
        return J({"data": [_look("look_iv_only")], "has_more": False, "next_token": None})
    if request.method == "GET" and p.startswith("/v3/avatars/looks/"):
        lid = p.rsplit("/", 1)[1]
        if lid == "lk_new":
            n = ETAT["polls"].get(lid, 0); ETAT["polls"][lid] = n + 1
            return J({"data": _look(lid, "private", "photo_avatar", "processing" if n < 1 else "completed")})
        return J({"data": _look(lid)})
    if request.method == "GET" and p == "/v3/users/me":
        b = ETAT["billing"]
        d = {"email": "x@y.z", "username": "u", "billing_type": b}
        if b == "subscription":
            d["subscription"] = {"credits": {"premium_credits": {"remaining": 700},
                                             "add_on_credits": {"remaining": 66}}}
        elif b == "wallet":
            d["wallet"] = {"remaining_balance": 12.5}
        else:
            d["usage_based"] = {"remaining_credits": 42.0}
        return J({"data": d})
    if request.method == "POST" and p == "/v3/videos":
        return J({"data": {"video_id": "v_1", "status": "waiting", "output_format": "mp4"}})
    if request.method == "GET" and p == "/v3/videos/v_1":
        return J({"data": {"id": "v_1", "status": "completed", "video_url": "https://cdn/v_1.mp4",
                           "thumbnail_url": None, "duration": 5.2}})
    if request.method == "GET" and p == "/v3/videos/v_fail":
        return J({"data": {"id": "v_fail", "status": "failed", "video_url": None,
                           "failure_code": "BAD_AVATAR", "failure_message": "Avatar not supported"}})
    if request.method == "POST" and p == "/v3/avatars":
        return J({"data": {"avatar_item": {"id": "lk_new", "name": "Test", "avatar_type": "photo_avatar",
                                           "group_id": "ag_new", "status": "processing"},
                           "avatar_group": {"id": "ag_new", "name": "Test", "status": "processing"}}})
    return J({"error": {"code": "not_found", "message": f"{request.method} {p}"}}, 404)


_REAL = httpx.AsyncClient
def _fake_client(*a, **k):
    k.pop("verify", None)
    return _REAL(*a, transport=httpx.MockTransport(handler), **k)


def brancher(mod):
    mod.httpx.AsyncClient = _fake_client
    if hasattr(mod, "invalidate_list_cache"):
        mod.invalidate_list_cache()


async def _sans_attente(_s):
    return None


# ── temoin : e88e4cc ─────────────────────────────────────────────────────────
OLD = None
try:
    _src = subprocess.run(["git", "show", "e88e4cc:backend/app/services/heygen_service.py"],
                          cwd=str(BACKEND.parent), capture_output=True).stdout
    if _src:
        _p = pathlib.Path(TMP) / "heygen_service_e88e4cc.py"
        _p.write_bytes(_src)
        _spec = importlib.util.spec_from_file_location("app.services._hs_e88e4cc", str(_p))
        OLD = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(OLD)
except Exception as e:
    print(f"  (temoin e88e4cc indisponible : {e})")


async def main():
    brancher(HS)
    HS.asyncio.sleep = _sans_attente
    c = HS.HeyGenClient()

    print("\n[1] voix : GET /v3/voices, privees puis publiques, pagination suivie")
    REQ.clear()
    try:
        v = await c.list_voices(use_cache=False)
    except Exception as e:
        v = [f"ERR {e}"]
    ids = [x.get("voice_id") for x in v if isinstance(x, dict)]
    check("1.1 trois voix, la privee d'abord, puis les deux pages publiques", ids == ["vc_mine", "vc_1", "vc_2"], _d(v))
    check("1.2 forme conservee pour l'UI : name, language, gender, preview_audio (= preview_audio_url), support_pause",
          bool(v) and isinstance(v[0], dict) and v[0].get("name") == "Ma voix" and v[0].get("preview_audio") == "https://a/mine.mp3"
          and v[1].get("language") == "English" and v[0].get("support_pause") is True, _d(v[:1]))
    check("1.3 la 2e page publique est lue avec token=p2 et limit=100",
          any(r[2] == "/v3/voices" and r[3].get("token") == "p2" and r[3].get("limit") == "100" for r in REQ), _d(REQ))

    print("\n[2] avatars : GET /v3/avatars/looks, prives puis publics")
    REQ.clear()
    try:
        a = await c.list_avatars(use_cache=False)
    except Exception as e:
        a = [f"ERR {e}"]
    aid = [x.get("avatar_id") for x in a if isinstance(x, dict)]
    check("2.1 trois looks : le mien d'abord, puis les deux pages publiques", aid == ["lk_mine", "look_iii", "look_iv_only"], _d(a))
    check("2.2 forme conservee : avatar_id, avatar_name, name, preview_image_url, avatar_type='avatar' pour tous",
          bool(a) and isinstance(a[0], dict) and a[0].get("avatar_name") == "Look lk_mine" and a[0].get("name") == "Look lk_mine"
          and a[0].get("preview_image_url") == "https://img/lk_mine.png"
          and all(x.get("avatar_type") == "avatar" for x in a if isinstance(x, dict)), _d(a[:1]))
    check("2.3 moteurs supportes transmis (supported_engines) et limit=50",
          bool(a) and isinstance(a[-1], dict) and a[-1].get("supported_engines") == ["avatar_v", "avatar_iv"]
          and any(r[2] == "/v3/avatars/looks" and r[3].get("limit") == "50" for r in REQ), _d(a[-1:]))

    print("\n[3] quota : GET /v3/users/me selon la facturation")
    res = {}
    for b in ("subscription", "wallet", "usage_based"):
        ETAT["billing"] = b
        try:
            res[b] = await c.remaining_quota()
        except Exception as e:
            res[b] = {"err": str(e)}
    check("3.1 abonnement : remaining_quota = premium + add-on (766), remaining_usd None",
          res["subscription"].get("remaining_quota") == 766 and res["subscription"].get("remaining_usd") is None, _d(res["subscription"]))
    check("3.2 portefeuille : remaining_usd = 12,5, remaining_quota None",
          res["wallet"].get("remaining_usd") == 12.5 and res["wallet"].get("remaining_quota") is None, _d(res["wallet"]))
    check("3.3 a l'usage : remaining_quota = 42, billing_type rendu",
          res["usage_based"].get("remaining_quota") == 42.0 and res["usage_based"].get("billing_type") == "usage_based", _d(res["usage_based"]))
    ETAT["billing"] = "subscription"

    print("\n[4] generation : moteur par defaut resolu par look, SSML converti")
    REQ.clear()
    ssml = '<speak>Le fond observe.<break time="1.5s"/>Nous montons.<break time="300ms"/>Maintenant.</speak>'
    out = {}
    for lk, eng in (("look_iii", None), ("look_iv_only", None), ("look_iii", "avatar_v")):
        try:
            vid = await c.generate_video_v3(ssml, lk, "vc_1", engine=eng)
            corps = [r[4] for r in REQ if r[0] == "POST" and r[2] == "/v3/videos"][-1]
            out[(lk, eng)] = (vid, corps)
        except Exception as e:
            out[(lk, eng)] = (f"ERR {e}", None)
    b1 = (out[("look_iii", None)][1] or {})
    check("4.1 sans moteur, look compatible Avatar III -> engine avatar_iii (decision : comme la v2)",
          b1.get("engine") == {"type": "avatar_iii"}, _d(out[("look_iii", None)]))
    check("4.2 sans moteur, look SANS Avatar III -> premier moteur supporte (avatar_v)",
          (out[("look_iv_only", None)][1] or {}).get("engine") == {"type": "avatar_v"}, _d(out[("look_iv_only", None)]))
    check("4.3 moteur explicite garde tel quel (avatar_v), sans lecture du look",
          (out[("look_iii", "avatar_v")][1] or {}).get("engine") == {"type": "avatar_v"}, _d(out[("look_iii", "avatar_v")]))
    sc = b1.get("script") or ""
    check("4.4 script : balises SSML retirees, pauses en ponctuation (temoin : le texte est la)",
          "Le fond observe" in sc and "Nous montons" in sc and "<" not in sc and ">" not in sc
          and sc.count("…") >= 1, _d(sc))
    check("4.5 le look est lu (GET /v3/avatars/looks/look_iii) avant la generation par defaut",
          any(r[0] == "GET" and r[2] == "/v3/avatars/looks/look_iii" for r in REQ), _d([r[:3] for r in REQ]))
    try:
        fin = await c.poll_video_status_v3("v_1")
    except Exception as e:
        fin = {"err": str(e)}
    check("4.6 statut v3 : completed -> video_url", fin.get("video_url") == "https://cdn/v_1.mp4", _d(fin))
    try:
        await c.poll_video_status_v3("v_fail")
        msg = "pas d'erreur"
    except Exception as e:
        msg = str(e)
    check("4.7 echec v3 : le message de la doc (failure_message) remonte", "Avatar not supported" in msg, _d(msg))

    print("\n[5] avatar depuis une photo : POST /v3/avatars puis statut du look")
    REQ.clear()
    img = pathlib.Path(TMP) / "visage.png"
    img.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="))
    try:
        r5 = await c.create_photo_avatar(img, "Mon visage")
    except Exception as e:
        r5 = {"err": str(e)}
    post = [r for r in REQ if r[0] == "POST" and r[2] == "/v3/avatars"]
    corps = post[0][4] if post else {}
    check("5.1 POST /v3/avatars type photo, name, fichier base64 image/png",
          isinstance(corps, dict) and corps.get("type") == "photo" and corps.get("name") == "Mon visage"
          and (corps.get("file") or {}).get("type") == "base64" and (corps.get("file") or {}).get("media_type") == "image/png"
          and bool((corps.get("file") or {}).get("data")), _d(corps))
    check("5.2 attend le statut completed du look, rend les cles historiques (photo_avatar_id = look)",
          r5.get("photo_avatar_id") == "lk_new" and r5.get("group_id") == "ag_new" and r5.get("status") == "completed"
          and r5.get("avatar_name") == "Mon visage"
          and sum(1 for r in REQ if r[2] == "/v3/avatars/looks/lk_new") >= 2, _d(r5, [r[:3] for r in REQ]))

    # MESURE 28/09 (preuve reelle) : un WebP nomme .jpg etait envoye en image/jpeg et refuse par HeyGen.
    from PIL import Image
    wj = pathlib.Path(TMP) / "apercu.jpg"
    Image.new("RGB", (8, 8), (200, 30, 30)).save(wj, "WEBP")
    REQ.clear(); ETAT["polls"].clear()
    try:
        await c.create_photo_avatar(wj, "Webp deguise")
    except Exception as e:
        print("   (erreur 5.3 :", e, ")")
    post = [r for r in REQ if r[0] == "POST" and r[2] == "/v3/avatars"]
    f3 = (post[0][4] or {}).get("file", {}) if post else {}
    brut = base64.b64decode(f3.get("data") or "") if f3.get("data") else b""
    check("5.3 WebP nomme .jpg : type lu dans les octets, converti en PNG (temoin : c'est bien un WebP sur disque)",
          wj.read_bytes()[8:12] == b"WEBP" and f3.get("media_type") == "image/png" and brut[:4] == b"\x89PNG",
          _d(f3.get("media_type"), str(brut[:8])))

    print("\n[6] plus aucun appel v1/v2 (temoin : e88e4cc en fait)")
    tous = [(r[1], r[2]) for r in REQ]
    check("6.1 ni /v1/ ni /v2/ ni upload.heygen.com dans les requetes de [5]",
          bool(tous) and not any(p.startswith(("/v1/", "/v2/")) or h == "upload.heygen.com" for h, p in tous), _d(tous))
    src = (BACKEND / "app" / "services" / "heygen_service.py").read_text(encoding="utf-8")
    code = "\n".join(l.split("#", 1)[0] for l in src.splitlines())
    check("6.2 le code de heygen_service.py ne contient plus aucun chemin /v1/ ou /v2/ ni upload.heygen.com",
          "/v3/videos" in code and "/v1/" not in code and "/v2/" not in code and "upload.heygen.com" not in code,
          _d([l.strip() for l in code.splitlines() if "/v1/" in l or "/v2/" in l][:5]))
    if OLD is not None:
        brancher(OLD)
        REQ.clear()
        try:
            await OLD.HeyGenClient().list_voices(use_cache=False)
        except Exception:
            pass
        check("6.3 temoin e88e4cc : list_voices appelle /v2/voices", any(r[2] == "/v2/voices" for r in REQ), _d(REQ))
    else:
        check("6.3 temoin e88e4cc importe", False, "git show a echoue")

    print("\n[7] pipeline : toute generation HeyGen passe par la v3")
    psrc = (BACKEND / "app" / "services" / "pipeline.py").read_text(encoding="utf-8")
    check("7.1 pipeline.py n'appelle plus heygen.generate_video( ni heygen.poll_video_status( (temoin : generate_video_v3 appele)",
          "self.heygen.generate_video_v3(" in psrc and "self.heygen.generate_video(" not in psrc
          and "self.heygen.poll_video_status(" not in psrc, "")
    check("7.2 use_avatar_iv conserve son sens : avatar_iv quand aucun moteur n'est choisi",
          'request.engine or ("avatar_iv" if getattr(request, "use_avatar_iv", False) else None)' in psrc, "")

    print("\n[8] cache des listes : memoire -> disque -> API (MESURE : 9 951 looks en 259 s)")
    HS.invalidate_list_cache()
    disque = HS._disk_path("voices")
    check("8.0 invalidate_list_cache efface le disque (temoin : chemin sous DATA_ROOT/cache)",
          not disque.exists() and disque.parent.name == "cache", _d(str(disque)))
    REQ.clear()
    v1 = await c.list_voices()
    n_api = sum(1 for r in REQ if r[2] == "/v3/voices")
    check("8.1 premier appel : API (3 pages) puis copie ecrite sur disque", n_api == 3 and disque.exists()
          and len(json.loads(disque.read_text(encoding="utf-8"))["items"]) == 3, _d(n_api, disque.exists()))
    HS._LIST_CACHE.clear()          # « redemarrage » : memoire vide, disque garde
    REQ.clear()
    v2 = await c.list_voices()
    check("8.2 apres redemarrage : liste relue du disque, AUCUN appel reseau (temoin : 3 voix rendues)",
          len(v2) == 3 and [x["voice_id"] for x in v2] == [x["voice_id"] for x in v1] and not REQ, _d(len(v2), REQ))
    d = json.loads(disque.read_text(encoding="utf-8")); d["t"] -= HS._LIST_CACHE_TTL + 60
    disque.write_text(json.dumps(d), encoding="utf-8")
    HS._LIST_CACHE.clear(); REQ.clear()
    v3 = await c.list_voices()
    servie_sans_attendre = len(v3) == 3 and not REQ
    t = HS._INFLIGHT.get("voices")
    if t is not None:
        await t
    check("8.3 copie perimee : servie tout de suite, puis rafraichie en arriere-plan (3 appels, date renouvelee)",
          servie_sans_attendre and sum(1 for r in REQ if r[2] == "/v3/voices") == 3
          and json.loads(disque.read_text(encoding="utf-8"))["t"] > d["t"] + 60, _d(servie_sans_attendre, len(REQ)))
    HS.invalidate_list_cache(); REQ.clear()
    a1, a2 = await asyncio.gather(c.list_voices(use_cache=False), c.list_voices(use_cache=False))
    check("8.4 deux demandes simultanees : UN seul parcours (3 appels, pas 6), meme resultat",
          sum(1 for r in REQ if r[2] == "/v3/voices") == 3 and a1 == a2 and len(a1) == 3,
          _d(sum(1 for r in REQ if r[2] == "/v3/voices")))
    HS.invalidate_list_cache(); REQ.clear()
    try:
        await c.list_avatars(use_cache=False)
    except Exception:
        pass
    check("8.5 la liste d'avatars passe par le meme cache (copie disque ecrite)",
          HS._disk_path("avatars").exists() and any(r[2] == "/v3/avatars/looks" for r in REQ), "")


asyncio.run(main())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
