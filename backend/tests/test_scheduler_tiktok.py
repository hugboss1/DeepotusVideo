# -*- coding: utf-8 -*-
"""TikTok Direct Post (plan scheduler T5 — tâche #27, 29/09/2026). Le VRAI httpx.AsyncClient envoie sur un MockTransport
(tests/fakehttp.py). Doc relue le 29/09 : creator_info AVANT l'init (la visibilité doit être une des options rendues),
morceaux de 5 à 64 Mo, total_chunk_count ARRONDI À L'INFÉRIEUR (le reste va au dernier morceau, 128 Mo au plus), 206
puis 201, client non audité = privé, refresh token qui PEUT CHANGER à chaque renouvellement (« You must use the
newly-returned token »), PKCE hexadécimal et loopback 127.0.0.1 pour une appli de bureau. Data-dir temporaire (le
refresh token renouvelé est écrit dans SON .env). Témoin : la base bdec0a1 n'a pas d'adaptateur TikTok.
Run : & $PY tests/test_scheduler_tiktok.py   (depuis backend/)"""
import asyncio, hashlib, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dztt_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from fakehttp import Recorder                                       # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


racine = pathlib.Path(__file__).resolve().parents[2]
_base = subprocess.run(["git", "ls-tree", "--name-only", "bdec0a1", "backend/app/services/"], cwd=racine,
                       capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base bdec0a1")
check("0.1 TÉMOIN : instagram_publisher.py oui, tiktok_publisher.py non", "instagram_publisher.py" in _base
      and "tiktok_publisher.py" not in _base)

from app.config import settings, ENV_FILE                           # noqa: E402
from app.services import marketing, tiktok_publisher as tp          # noqa: E402

rec = Recorder()
tp._client = rec.factory
tp.POLL_EVERY_S = 0
MO = 1024 * 1024
SECRET, RT = "tt-client-secret-du-banc", "rft.refresh-du-banc"
vid = _tmp / "tt.mp4"
vid.write_bytes(bytes(range(256)) * 4)                             # 1 024 octets : un seul morceau
N = vid.stat().st_size


def jeton(rt=RT, expire=86400):
    return httpx.Response(200, json={"access_token": "act.1", "expires_in": expire, "refresh_token": rt,
                                     "refresh_expires_in": 31536000, "token_type": "Bearer"})


def createur(opts=("SELF_ONLY",), **k):
    return httpx.Response(200, json={"data": {"privacy_level_options": list(opts), "comment_disabled": k.get("cd", False),
                                              "duet_disabled": False, "stitch_disabled": True,
                                              "max_video_post_duration_sec": 600}, "error": {"code": "ok"}})


def init_ok(pid="v_pub_file~1"):
    return httpx.Response(200, json={"data": {"publish_id": pid, "upload_url": "https://open-upload.tiktokapis.com/video/?upload_id=1"},
                                     "error": {"code": "ok", "message": ""}})


def statut(s, **k):
    return httpx.Response(200, json={"data": {"status": s, **k}, "error": {"code": "ok"}})


async def main():
    print("\n[1] clés, registre, morceaux")
    for k in ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"):
        setattr(settings, k, "")
    settings.TIKTOK_AUDITED = False
    check("1.1 sans clés : tiktok indisponible", not settings.has_tiktok and "tiktok" not in marketing.auto_channels())
    settings.TIKTOK_CLIENT_KEY, settings.TIKTOK_CLIENT_SECRET = "awck", SECRET
    check("1.2 client sans refresh token : indisponible (l'autorisation n'a pas eu lieu)", not settings.has_tiktok)
    settings.TIKTOK_REFRESH_TOKEN = RT
    check("1.3 les trois clés posées : disponible", settings.has_tiktok and "tiktok" in marketing.auto_channels())
    _p = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, '.'); import app.main; "
                         "from app.services import publishers as P; print(sorted(P._REGISTRY))"],
                        cwd=str(racine / "backend"), capture_output=True, text=True,
                        env=dict(os.environ, DEEPOTUS_DATA_DIR=str(_tmp / "neuf")))
    lignes = _p.stdout.strip().splitlines()
    check("1.4 l'application seule (import app.main) enregistre tiktok", _p.returncode == 0 and lignes
          and "tiktok" in json.loads(lignes[-1].replace("'", '"')), (_p.stdout + _p.stderr)[-300:])
    cas = {1000: (1000, 1), 5 * MO - 1: (5 * MO - 1, 1), 64 * MO: (64 * MO, 1), 70 * MO: (tp.CHUNK, 70 * MO // tp.CHUNK),
           4096 * MO: (tp.CHUNK, 4096 * MO // tp.CHUNK)}
    check("1.5 découpage selon la doc : un seul morceau jusqu'à 64 Mo, sinon total ARRONDI À L'INFÉRIEUR",
          all(tp._chunks(s) == attendu for s, attendu in cas.items()), str({s: tp._chunks(s) for s in cas}))
    check("1.6 bornes : morceau entre 5 et 64 Mo, dernier morceau ≤ 128 Mo, 1000 morceaux au plus",
          5 * MO <= tp.CHUNK <= 64 * MO and all(s - (n - 1) * c <= 128 * MO and n <= 1000
                                                 for s in (70 * MO, 4096 * MO, 64 * MO + 1) for c, n in [tp._chunks(s)]))

    print("\n[2] autorisation : loopback et PKCE hexadécimal")
    u = httpx.URL(tp.auth_url("s1"))
    q = dict(u.params)
    check("2.1 point d'autorisation TikTok v2, loopback 127.0.0.1 sur le port du backend, portées publication + lecture",
          str(u).startswith("https://www.tiktok.com/v2/auth/authorize/?") and q.get("client_key") == "awck"
          and q.get("redirect_uri") == f"http://127.0.0.1:{settings.PORT}/api/oauth/tiktok/callback/"
          and set(q.get("scope", "").split(",")) >= {"video.publish", "video.list"} and q.get("state") == "s1", str(q))
    rec.calls.clear()
    rec.script[:] = [jeton(rt="rft.neuf")]
    got = await tp.exchange_code("code-tt", "s1")
    f = rec.calls[0].form() if rec.calls else {}
    check("2.2 PKCE S256 en HEXADÉCIMAL (doc Login Kit Desktop) : le défi est le sha256 hex du vérificateur envoyé",
          got == "rft.neuf" and q.get("code_challenge_method") == "S256"
          and hashlib.sha256(f.get("code_verifier", "").encode()).hexdigest() == q.get("code_challenge")
          and f.get("grant_type") == "authorization_code" and f.get("redirect_uri") == q.get("redirect_uri"), str(f))
    rec.calls.clear()
    check("2.3 état inconnu ou déjà consommé : refus SANS réseau", await tp.exchange_code("code-tt", "s1") == "" and not rec.calls)

    print("\n[3] un envoi, client non audité")
    tp._oublier_jeton()
    rec.calls.clear()
    rec.script[:] = [jeton(), createur(("SELF_ONLY",)), init_ok(), httpx.Response(201),
                     statut("PROCESSING_UPLOAD"), statut("PUBLISH_COMPLETE", publicaly_available_post_id=[])]
    res = await tp.publish("Légende tiktok", str(vid), None, {"privacy": "PUBLIC_TO_EVERYONE"})
    check("3.1 publié en PRIVÉ, et c'est DIT (client non audité) ; sans id public, l'id de publication sert de référence",
          res.ok and res.remote_id == "v_pub_file~1" and "PRIVÉ" in res.detail and "audit" in res.detail, str(res))
    c = rec.calls + [None] * 6
    tok, cre, ini, put = c[:4]
    check("3.2 creator_info D'ABORD, jeton porteur", cre and cre.method == "POST"
          and cre.url == "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
          and cre.headers.get("authorization") == "Bearer act.1")
    b = json.loads(ini.body) if ini else {}
    check("3.3 init : SELF_ONLY forcé, FILE_UPLOAD aux tailles RÉELLES, points coupés que le créateur a coupés",
          ini and ini.url == "https://open.tiktokapis.com/v2/post/publish/video/init/"
          and b.get("post_info", {}).get("privacy_level") == "SELF_ONLY" and b["post_info"].get("title") == "Légende tiktok"
          and b["post_info"].get("disable_stitch") is True and b["post_info"].get("disable_comment") is False
          and b.get("source_info") == {"source": "FILE_UPLOAD", "video_size": N, "chunk_size": N, "total_chunk_count": 1}, str(b))
    check("3.4 PUT du morceau : Content-Range, Content-Length, octet pour octet", put and put.method == "PUT"
          and put.headers.get("content-range") == f"bytes 0-{N - 1}/{N}" and put.headers.get("content-length") == str(N)
          and put.headers.get("content-type") == "video/mp4" and put.body == vid.read_bytes(), str(put.headers if put else None))

    print("\n[4] le jeton : mis en cache, et le refresh token renouvelé est GARDÉ")
    rec.calls.clear()
    rec.script[:] = [createur(("SELF_ONLY",)), init_ok("p2"), httpx.Response(201), statut("PUBLISH_COMPLETE")]
    res = await tp.publish("x", str(vid), None, {})
    check("4.1 un second envoi dans les 24 h réutilise le jeton d'accès (6 requêtes/min par jeton : pas d'appel inutile)",
          res.ok and not any("oauth/token" in k.url for k in rec.calls), str([k.url for k in rec.calls]))
    tp._oublier_jeton()
    rec.script[:] = [jeton(rt="rft.tourne"), createur(("SELF_ONLY",)), init_ok("p3"), httpx.Response(201), statut("PUBLISH_COMPLETE")]
    res = await tp.publish("x", str(vid), None, {})
    env = ENV_FILE.read_text("utf-8") if ENV_FILE.exists() else ""
    check("4.2 TikTok rend un NOUVEAU refresh token : appliqué ET écrit (.env du data-dir, pas de coffre ici)",
          res.ok and settings.TIKTOK_REFRESH_TOKEN == "rft.tourne" and "TIKTOK_REFRESH_TOKEN=rft.tourne" in env, env[-200:])
    tp._oublier_jeton()
    rec.calls.clear()
    rec.script[:] = [jeton(rt="rft.tourne"), createur(("SELF_ONLY",)), init_ok("p4"), httpx.Response(201), statut("PUBLISH_COMPLETE")]
    await tp.publish("x", str(vid), None, {})
    check("4.3 le renouvellement suivant envoie bien le refresh token GARDÉ", rec.calls and rec.calls[0].form().get("refresh_token") == "rft.tourne")

    print("\n[5] client audité")
    settings.TIKTOK_AUDITED = True
    rec.calls.clear()
    rec.script[:] = [createur(("PUBLIC_TO_EVERYONE", "SELF_ONLY")), init_ok("p5"), httpx.Response(201),
                     statut("PUBLISH_COMPLETE", publicaly_available_post_id=[7350001])]
    res = await tp.publish("x", str(vid), None, {})
    b = json.loads(rec.calls[1].body) if len(rec.calls) > 1 else {}
    check("5.1 audité : public demandé et accordé, id public rendu, aucune mention de privé",
          res.ok and res.remote_id == "7350001" and "PRIVÉ" not in res.detail
          and b.get("post_info", {}).get("privacy_level") == "PUBLIC_TO_EVERYONE", str((res, b.get("post_info"))))
    rec.calls.clear()
    rec.script[:] = [createur(("SELF_ONLY", "MUTUAL_FOLLOW_FRIENDS"))]
    res = await tp.publish("x", str(vid), None, {"privacy": "PUBLIC_TO_EVERYONE"})
    check("5.2 visibilité absente des options du créateur : refus AVANT l'init, options nommées",
          not res.ok and "PUBLIC_TO_EVERYONE" in res.detail and "SELF_ONLY" in res.detail and len(rec.calls) == 1, str(res))
    settings.TIKTOK_AUDITED = False

    print("\n[6] refus parlants")
    rec.script[:] = [createur(("SELF_ONLY",)),
                     httpx.Response(403, json={"data": {}, "error": {"code": "unaudited_client_can_only_post_to_private_accounts",
                                                                      "message": "..."}})]
    res = await tp.publish("x", str(vid), None, {})
    check("6.1 compte public + client non audité : le code TikTok ET ce qu'il faut faire (passer le compte en privé)",
          not res.ok and "unaudited_client_can_only_post_to_private_accounts" in res.detail and "privé" in res.detail, str(res))
    rec.script[:] = [createur(("SELF_ONLY",)),
                     httpx.Response(403, json={"data": {}, "error": {"code": "spam_risk_too_many_posts", "message": "..."}})]
    res = await tp.publish("x", str(vid), None, {})
    check("6.2 trop de posts : le code remonte", not res.ok and "spam_risk_too_many_posts" in res.detail, str(res))
    rec.script[:] = [createur(("SELF_ONLY",)), init_ok(), httpx.Response(500, text="panne")]
    res = await tp.publish("x", str(vid), None, {})
    check("6.3 PUT refusé : morceau nommé", not res.ok and "tiktok upload 500" in res.detail and "1/1" in res.detail, str(res))
    rec.script[:] = [createur(("SELF_ONLY",)), init_ok(), httpx.Response(201), statut("FAILED", fail_reason="duration_check_failed")]
    res = await tp.publish("x", str(vid), None, {})
    check("6.4 FAILED : la raison de TikTok remonte", not res.ok and "duration_check_failed" in res.detail, str(res))
    rec.calls.clear()
    rec.script[:] = [createur(("SELF_ONLY",)), init_ok(), httpx.Response(201)] + [statut("PROCESSING_UPLOAD")] * tp.POLL_MAX
    res = await tp.publish("x", str(vid), None, {})
    check("6.5 jamais PUBLISH_COMPLETE : refus après POLL_MAX sondages, pas un de plus", not res.ok and "PUBLISH_COMPLETE" in res.detail
          and len(rec.calls) == 3 + tp.POLL_MAX, str((res, len(rec.calls))))
    check("6.6 sondage : 30 requêtes/min au plus (doc get-video-status), 5 minutes au plus",
          tp.POLL_EVERY_S_DEFAUT >= 2 and tp.POLL_EVERY_S_DEFAUT * tp.POLL_MAX <= 300, str((tp.POLL_EVERY_S_DEFAUT, tp.POLL_MAX)))
    tp._oublier_jeton()
    rec.calls.clear()
    envoye = settings.TIKTOK_REFRESH_TOKEN                          # la réponse renvoie le jeton RÉELLEMENT envoyé
    rec.script[:] = [httpx.Response(400, json={"error": "invalid_grant", "error_description": f"bad {envoye} / {SECRET}"})]
    res = await tp.publish("x", str(vid), None, {})
    check("6.7 refresh refusé : dit, sans aucune clé dans le message", not res.ok and "tiktok token 400" in res.detail
          and SECRET not in res.detail and "rft." not in res.detail and len(rec.calls) == 1, str(res))
    rec.calls.clear()
    res = await tp.publish("x", None, str(vid), {})
    check("6.8 pas de vidéo : refus SANS réseau", not res.ok and "vidéo" in res.detail and not rec.calls, str(res))

    print("\n[7] plusieurs morceaux (vrais octets, bornes rabaissées pour le banc)")
    tp.CHUNK, tp.SINGLE_MAX = 400, 400
    rec.calls.clear()
    rec.script[:] = [jeton(), createur(("SELF_ONLY",)), init_ok(), httpx.Response(206), httpx.Response(201), statut("PUBLISH_COMPLETE")]
    tp._oublier_jeton()
    res = await tp.publish("x", str(vid), None, {})
    puts = [k for k in rec.calls if k.method == "PUT"]
    ib = json.loads(rec.calls[2].body) if len(rec.calls) > 2 else {}
    check("7.1 1 024 octets en morceaux de 400 : DEUX morceaux (arrondi inférieur), le reste va au dernier (400 + 624)",
          res.ok and ib.get("source_info", {}).get("total_chunk_count") == 2 and [len(p.body) for p in puts] == [400, 624]
          and [p.headers.get("content-range") for p in puts] == ["bytes 0-399/1024", "bytes 400-1023/1024"]
          and b"".join(p.body for p in puts) == vid.read_bytes(), str((ib.get("source_info"), [p.headers.get("content-range") for p in puts])))

    print("\n[8] statistiques")
    rec.calls.clear()
    rec.script[:] = [httpx.Response(200, json={"data": {"videos": [{"id": 7350001, "view_count": 12, "like_count": 3,
                                                                   "comment_count": 1, "share_count": 2}]}, "error": {"code": "ok"}})]
    st = await tp.fetch_stats(["7350001", "v_pub_file~1"])
    q = rec.calls[0] if rec.calls else None
    check("8.1 video/query : ids NUMÉRIQUES seulement (une référence de publication privée n'en est pas un), compteurs lus",
          st == {"7350001": {"views": 12, "likes": 3, "comments": 1, "shares": 2, "saves": 0}}
          and q and json.loads(q.body)["filters"]["video_ids"] == ["7350001"], str(st))
    rec.calls.clear()
    check("8.2 aucun id numérique : aucun appel", await tp.fetch_stats(["v_pub_file~1"]) == {} and not rec.calls)

asyncio.run(main())

print("\n[9] où va le refresh token renouvelé (coffre.enregistrer_cle)")
from app.services import coffre                                     # noqa: E402
avant = ENV_FILE.read_text("utf-8")
coffre.poser("mot-de-passe-du-banc", {})
coffre.ouvrir("mot-de-passe-du-banc")
ou = coffre.enregistrer_cle("TIKTOK_REFRESH_TOKEN", "rft.au-coffre")
check("9.1 coffre OUVERT : dans le coffre, appliqué, et le .env n'est PAS touché (jamais un secret en clair)",
      ou == "coffre" and coffre.lire_cle("TIKTOK_REFRESH_TOKEN") == "rft.au-coffre"
      and settings.TIKTOK_REFRESH_TOKEN == "rft.au-coffre" and ENV_FILE.read_text("utf-8") == avant, ou)
coffre.fermer()
ou = coffre.enregistrer_cle("TIKTOK_REFRESH_TOKEN", "rft.coffre-ferme")
check("9.2 coffre posé mais FERMÉ : appliqué en mémoire seulement, rien d'écrit en clair",
      ou == "memoire" and settings.TIKTOK_REFRESH_TOKEN == "rft.coffre-ferme" and "rft.coffre-ferme" not in ENV_FILE.read_text("utf-8"), ou)
coffre.ouvrir("mot-de-passe-du-banc")
check("9.3 rouvert, le coffre a gardé la valeur écrite quand il était ouvert", coffre.lire_cle("TIKTOK_REFRESH_TOKEN") == "rft.au-coffre")
coffre.fermer()
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
