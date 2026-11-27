# -*- coding: utf-8 -*-
"""t322 (Compagnon M5, 26/11/2026) — POST /api/sync/post : un contenu neuf rédigé sur le téléphone devient un brouillon du
PC APRÈS les gardes rejouées ici (12 mots, mots interdits, source, visuel ≠ capture). Aucun réseau.
  T1  témoin : la base (t321, 8e08b9d2) n'a ni sync_post ni la route ouverte
  P1  sans jeton : 401 ; un post propre -> brouillon dans l'espace, demain 9 h, source JAMAIS dans un champ publiable
  P2  renvoi identique : « deja », même post, un seul post en base ; même id autre corps : 409 conflit
  P3  refus 409 : 12 mots repris, mot interdit, source citée ; rien d'écrit
  P4  visuel : absent de la Bibliothèque -> 409 reessayer ; égal à la capture (sha256) -> 409 visuel_capte ;
      un visuel neuf -> source_image posé et source notée dans la recette du visuel
  P5  forme : 400 (id, titre vide, référence manquante, empreinte de capture) ; espace inconnu 404 ; archivé 409
  P6  la route est ouverte au Wi-Fi
Run (depuis backend/) : & $PY tests/test_sync_post.py"""
import asyncio, hashlib, io, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsyncpost_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent)); sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "8e08b9d2"
r0 = subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/sync_post.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/main.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 témoin : la base n'a ni sync_post ni /sync/post ouverte",
      r0.returncode != 0 and r1.returncode == 0 and b"/api/sync/post" not in r1.stdout)

from fastapi.testclient import TestClient                           # noqa: E402
from PIL import Image                                               # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import _jeton_appareil as JA                                        # noqa: E402
from app.services import espaces as E, inspiration as INS, sync_post as SP  # noqa: E402
from app.services.storage import LibraryAsset, ScheduledPost, async_session_factory  # noqa: E402
from sqlalchemy import select                                       # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
LAN = ("192.168.1.42", 50000)
CAPTE = ("Les dix meilleures astuces pour garder un pain croustillant toute la semaine sans jamais le mettre au "
         "réfrigérateur ni le congeler selon les boulangers")
INTERDITS = {"eid": None}


async def _interdits(eid):
    return ["discount"]
INS._interdits = _interdits


def png(couleur) -> bytes:
    b = io.BytesIO(); Image.new("RGB", (16, 16), couleur).save(b, "PNG"); return b.getvalue()


CAPTURE = png((200, 10, 10))
NEUF = png((10, 200, 10))
(_tmp / "images" / "neuf.png").write_bytes(NEUF)
(_tmp / "images" / "capture.png").write_bytes(CAPTURE)


def corps(ident="el-1", **post):
    p = {"title": "Un pain qui chante", "caption": "Notre astuce maison : un torchon de lin et une boîte en bois.",
         "hook": "Croustillant jusqu'à dimanche", "status": "draft", "run_at": "2026-11-27T09:00:00", "espace_id": eid,
         "source_image": None}
    p.update(post)
    return {"id": ident, "post": p, "etat": "brouillon", "visuel": None, "reference": CAPTE,
            "inspiration": {"id": "ins-1", "source": {"libelle": "@boulangerie.rivale", "lien": "https://exemple.org/astuce", "le": "2026-11-26"},
                            "capture_sha256": hashlib.sha256(CAPTURE).hexdigest(), "garde": {"suite": 0, "proximite": 0}, "angle": "Le lin"}}


def posts():
    async def _l():
        async with async_session_factory() as s:
            return list((await s.execute(select(ScheduledPost))).scalars())
    return asyncio.run(_l())


with TestClient(app, client=("127.0.0.1", 50001)) as loc:
    E.lire()
    eid = E.creer({"nom": "Boulangerie Lune"})["id"]
    lan = TestClient(app, client=LAN)
    H = JA.entetes(app)

    print("[P] dépôt")
    check("P1a sans jeton : 401", lan.post("/api/sync/post", json=corps()).status_code == 401)
    r = lan.post("/api/sync/post", headers=H, json=corps())
    b = r.json() if r.status_code == 200 else {}
    ps = posts()
    check("P1b brouillon créé dans l'espace, statut draft, run_at demain 9 h", r.status_code == 200 and b.get("statut") == "cree"
          and len(ps) == 1 and ps[0].espace_id == eid and ps[0].status == "draft" and ps[0].run_at.hour == 9, r.text[:300])
    check("P1c la source n'est dans AUCUN champ publiable", ps and all("exemple.org" not in str(getattr(ps[0], k) or "") and "rivale" not in str(getattr(ps[0], k) or "")
                                                                        for k in ("title", "caption", "hook", "brief")))
    reg = json.loads(E.chemin(eid, SP.FICHIER).read_text(encoding="utf-8"))
    check("P1d registre du téléphone : source et garde notées, PAS le texte capté",
          any(v.get("source", {}).get("lien") == "https://exemple.org/astuce" for v in reg["recus"].values())
          and "croustillant toute la semaine" not in json.dumps(reg, ensure_ascii=False))

    r = lan.post("/api/sync/post", headers=H, json=corps())
    check("P2a renvoi identique : « deja », même post, toujours un seul", r.status_code == 200 and r.json().get("statut") == "deja"
          and r.json().get("post_id") == b.get("post_id") and len(posts()) == 1, r.text[:200])
    r = lan.post("/api/sync/post", headers=H, json=corps(title="Autre titre"))
    check("P2b même id, autre corps : 409 conflit", r.status_code == 409 and r.json()["detail"]["code"] == "conflit")

    copie = corps("el-2", caption="Voici " + " ".join(CAPTE.split()[:13]))
    r = lan.post("/api/sync/post", headers=H, json=copie)
    check("P3a 13 mots repris : 409 copie", r.status_code == 409 and r.json()["detail"]["code"] == "copie", r.text[:200])
    r = lan.post("/api/sync/post", headers=H, json=corps("el-3", caption="Un discount pour vous"))
    check("P3b mot interdit du PC : 409 interdits", r.status_code == 409 and r.json()["detail"]["code"] == "interdits", r.text[:200])
    r = lan.post("/api/sync/post", headers=H, json=corps("el-4", caption="Vu sur exemple.org/astuce"))
    check("P3c source citée : 409 source", r.status_code == 409 and r.json()["detail"]["code"] == "source", r.text[:200])
    check("P3d aucun post de plus", len(posts()) == 1)

    c = corps("el-5", source_image="neuf.png"); c["visuel"] = {"nom": "absent.png", "sha256": "0" * 64}
    r = lan.post("/api/sync/post", headers=H, json=c)
    check("P4a visuel pas encore déposé : 409 reessayer", r.status_code == 409 and r.json()["detail"]["code"] == "reessayer", r.text[:200])
    c = corps("el-6"); c["visuel"] = {"nom": "capture.png", "sha256": hashlib.sha256(CAPTURE).hexdigest()}
    r = lan.post("/api/sync/post", headers=H, json=c)
    check("P4b visuel = capture : 409 visuel_capte", r.status_code == 409 and r.json()["detail"]["code"] == "visuel_capte", r.text[:200])

    async def _asset():
        async with async_session_factory() as s:
            s.add(LibraryAsset(filename="neuf.png", recette=json.dumps({"moteur": "fal"})))
            await s.commit()
    try:
        asyncio.run(_asset())
    except Exception as e:                                          # noqa: BLE001
        print("  (fiche Bibliothèque non créée :", type(e).__name__, ")")
    c = corps("el-7"); c["visuel"] = {"nom": "neuf.png", "sha256": hashlib.sha256(NEUF).hexdigest()}
    r = lan.post("/api/sync/post", headers=H, json=c)
    p7 = [p for p in posts() if p.id == (r.json() or {}).get("post_id")]
    check("P4c visuel neuf : source_image posé", r.status_code == 200 and p7 and p7[0].source_image == "neuf.png", r.text[:200])

    async def _rec():
        async with async_session_factory() as s:
            row = await s.get(LibraryAsset, "neuf.png")
            return json.loads(row.recette) if row and row.recette else {}
    rec = asyncio.run(_rec())
    check("P4d la source est notée dans la recette du visuel (origine telephone)",
          rec.get("inspiration", {}).get("origine") == "telephone" and rec["inspiration"]["source"]["lien"] == "https://exemple.org/astuce", str(rec)[:200])

    for lab, c in (("id", dict(corps(), id="a b")), ("titre vide", corps("el-8", title=" ")),
                   ("référence", {k: v for k, v in corps("el-9").items() if k != "reference"}),
                   ("empreinte", {**corps("el-10"), "inspiration": {**corps()["inspiration"], "capture_sha256": "zz"}})):
        r = lan.post("/api/sync/post", headers=H, json=c)
        check(f"P5 forme ({lab}) : 400", r.status_code == 400, r.text[:150])
    r = lan.post("/api/sync/post", headers=H, json=corps("el-11", espace_id="inconnu"))
    check("P5 espace inconnu : 404", r.status_code == 404)
    E.archiver(eid)
    r = lan.post("/api/sync/post", headers=H, json=corps("el-12"))
    check("P5 espace archivé : 409", r.status_code == 409 and r.json()["detail"]["code"] == "espace")
    E.archiver(eid, False)
    check("P6 ouverte au Wi-Fi", ("POST", "/api/sync/post") in _MAIN._ECRITURES_OUVERTES)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
