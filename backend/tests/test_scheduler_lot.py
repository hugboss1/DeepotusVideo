# -*- coding: utf-8 -*-
"""Lot exportable (plan scheduler T12, D1 part backend — tâche #32 PR1, 30/09/2026) : seuls les posts VALIDÉS de la
fenêtre sortent, chacun avec son média (URL locale, taille, sha256 du fichier réel) ; le retour d'état du compagnon
fond le résultat, compte le quota PARTAGÉ, refuse d'écraser un post publié par un autre porteur (409), rend un échec
reprenable (ready, jamais failed) — et, écart au plan, refuse qu'un « échec » dépublie un post déjà publié. Aucun jeton
ne sort. Une seule boucle asynchrone (ASGITransport), data-dir temporaire, clés vidées. Témoin : la base afd75e5 n'a
ni /schedule/lot ni /report.
Run : & $PY tests/test_scheduler_lot.py   (depuis backend/)"""
import asyncio, hashlib, json, os, pathlib, subprocess, sys, tempfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzlot_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


racine = pathlib.Path(__file__).resolve().parents[2]
_r = subprocess.run(["git", "show", "afd75e5:backend/app/api/routes.py"], cwd=racine, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base afd75e5")
check("0.1 TÉMOIN : ni /schedule/lot ni /schedule/{id}/report", _r and "/schedule/lot" not in _r and "/schedule/{post_id}/report" not in _r)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.IMAGES_FOLDER = os.environ["IMAGES_FOLDER"]
SECRETS = {"X_API_KEY": "xk-SECRET", "TELEGRAM_BOT_TOKEN": "1:tg-SECRET", "YOUTUBE_REFRESH_TOKEN": "1//yt-SECRET",
           "IG_ACCESS_TOKEN": "EAA-ig-SECRET", "TIKTOK_REFRESH_TOKEN": "rft.SECRET"}
for _k, _v in SECRETS.items():
    setattr(settings, _k, _v)                                        # posés : ils ne doivent JAMAIS sortir par le lot
from httpx import AsyncClient, ASGITransport                       # noqa: E402
from app.main import app                                            # noqa: E402
from app.services.storage import init_db                            # noqa: E402
from app.services import quota                                      # noqa: E402

IMG = settings.images_path
IMG.mkdir(parents=True, exist_ok=True)
(IMG / "lot.png").write_bytes(b"PNG-de-banc" * 40)
SHA = hashlib.sha256((IMG / "lot.png").read_bytes()).hexdigest()


async def main():
    await init_db()
    soon = (datetime.utcnow() + timedelta(hours=3)).isoformat() + "Z"
    loin = (datetime.utcnow() + timedelta(days=20)).isoformat() + "Z"
    async with AsyncClient(transport=ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://test") as c:
        async def mk(**k):
            return (await c.post("/api/schedule", json=k)).json()["id"]

        async def ligne(pid):
            return next(q for q in (await c.get("/api/schedule")).json() if q["id"] == pid)

        a = await mk(title="Avec média", caption="légende A", channels=["x", "telegram"], run_at=soon, source_image="lot.png",
                     brief={"tg_caption": "version Telegram", "hashtags": "#Deepotus", "links": "https://deepotus.example"})
        b = await mk(title="Sans média", caption="légende B", channels=["x"], run_at=soon)
        d = await mk(title="Brouillon", caption="d", channels=["x"], run_at=soon, source_image="lot.png")
        lointain = await mk(title="Loin", caption="l", channels=["x"], run_at=loin, source_image="lot.png")
        lo = (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z"
        v = (await c.post("/api/schedule/validate", json={"from": lo, "to": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"})).json()
        await c.patch(f"/api/schedule/{d}", json={"caption": "d modifiée"})          # dévalidé : ne doit pas sortir
        ancien = await mk(title="Auto jamais validé", caption="e", channels=["x"], run_at=soon, source_image="lot.png",
                          status="scheduled", mode="auto")                      # créé APRÈS la validation : auto mais jamais validé

        print("\n[1] le lot")
        r = await c.get("/api/schedule/lot", params={"days": 7})
        lot = r.json()
        ids = [p["id"] for p in lot.get("posts", [])]
        check("1.1 seuls les posts VALIDÉS de la fenêtre sortent (ni le nu, ni le dévalidé, ni le lointain, ni l'auto jamais validé)",
              r.status_code == 200 and ids == [a] and b in [x["id"] for x in v["skipped"]] and lointain in v["validated"], str(ids))
        p = (lot.get("posts") or [{}])[0]
        check("1.2 légende, variante Telegram, hashtags, liens, canaux, heure UTC", p.get("caption") == "légende A"
              and p.get("tg_caption") == "version Telegram" and p.get("hashtags") == "#Deepotus"
              and p.get("links") == "https://deepotus.example" and p.get("channels") == ["x", "telegram"]
              and str(p.get("run_at", "")).endswith("Z"), str(p)[:300])
        check("1.3 le média : URL locale, nom, taille et sha256 du FICHIER RÉEL, et l'aperçu",
              p.get("media") == {"kind": "image", "url": "/api/images/lot.png", "filename": "lot.png",
                                 "bytes": len(b"PNG-de-banc" * 40), "sha256": SHA}
              and p.get("preview") == f"/api/schedule/{a}/preview.png", str(p.get("media")))
        check("1.4 plafonds et bornes joints (TikTok privé sans audit dit)", lot.get("quotas", {}).get("x", {}).get("limit") == 500
              and "tiktok" in lot.get("notes", {}) and "x" in lot.get("notes", {}), str(lot.get("notes"))[:200])
        check("1.5 AUCUN jeton ne sort par le lot", not any(v_ in r.text for v_ in SECRETS.values()))
        r30 = (await c.get("/api/schedule/lot", params={"days": 30})).json()
        check("1.6 la fenêtre s'élargit avec days (le lointain entre à 30 jours)", lointain in [x["id"] for x in r30["posts"]])
        r0 = await c.get("/api/schedule/lot", params={"days": 0})
        check("1.7 days borné : 0 → 1 jour (le post à +3 h sort), pas une fenêtre vide ni une erreur",
              r0.status_code == 200 and [x["id"] for x in r0.json()["posts"]] == [a], r0.text[:200])

        print("\n[2] le retour d'état")
        r = await c.post(f"/api/schedule/{a}/report", json={"status": "posted", "published_by": "iPhone d'Olivier",
                                                              "remote_ids": {"x": "1900", "telegram": "42"}})
        row = await ligne(a)
        check("2.1 publié par le compagnon : statut, porteur, ids distants, x_post_id", r.json().get("ok") is True
              and row["status"] == "posted" and row["published_by"] == "iPhone d'Olivier"
              and row["remote_ids"] == {"x": "1900", "telegram": "42"} and row["x_post_id"] == "1900", str(row)[:300])
        check("2.2 le plafond du réseau est PARTAGÉ : X compté (Telegram n'a pas de plafond)", quota.used("x") == 1 and quota.used("telegram") == 0)
        r = await c.post(f"/api/schedule/{a}/report", json={"status": "posted", "published_by": "iPhone d'Olivier",
                                                              "remote_ids": {"x": "1900", "telegram": "42"}})
        check("2.3 le MÊME porteur qui répète : idempotent, rien recompté", r.status_code == 200 and quota.used("x") == 1, r.text[:200])
        r = await c.post(f"/api/schedule/{a}/report", json={"status": "posted", "published_by": "Pixel", "remote_ids": {"x": "9999"}})
        row = await ligne(a)
        check("2.4 un AUTRE porteur : 409, rien réécrit, rien recompté", r.status_code == 409
              and row["remote_ids"]["x"] == "1900" and quota.used("x") == 1, r.text[:200])
        r = await c.post(f"/api/schedule/{a}/report", json={"status": "failed", "published_by": "iPhone d'Olivier", "error": "oups"})
        row = await ligne(a)
        check("2.5 un « échec » ne dépublie JAMAIS un post publié (écart au plan)", r.status_code == 409 and row["status"] == "posted", r.text[:200])
        r = await c.post(f"/api/schedule/{b}/report", json={"status": "failed", "published_by": "iPhone d'Olivier", "error": "hors réseau"})
        row = await ligne(b)
        check("2.6 un échec rapporté rend le post reprenable par le PC (ready), jamais failed, la raison gardée",
              row["status"] == "ready" and "hors réseau" in (row["error"] or ""), str(row)[:200])
        check("2.7 post inconnu : 404 ; statut illisible : 400",
              (await c.post("/api/schedule/inconnu/report", json={"status": "posted"})).status_code == 404
              and (await c.post(f"/api/schedule/{b}/report", json={"status": "peut-être"})).status_code == 400)

asyncio.run(main())
print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
