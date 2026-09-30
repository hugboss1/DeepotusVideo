# -*- coding: utf-8 -*-
"""Aperçus verticaux (plan scheduler T9 — tâche #30, 30/09/2026). Banc-miroir : on lit les PIXELS du PNG rendu.
540×960 ; bande haute, rail droit et bande basse ASSOMBRIS sur le visuel (zones d'interface du lecteur), cœur du
visuel intact, légende écrite DANS la bande basse ; un visuel paysage est recadré (cover), pas écrasé ; sans visuel,
un gabarit 9:16 ; X et Telegram inchangés ; la route sert le PNG pour les trois canaux verticaux.
Témoin : la base 09621e3 n'a pas de SAFE_ZONES.
Run : & $PY tests/test_scheduler_preview.py   (depuis backend/)"""
import io, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzprev_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
(_tmp / "images").mkdir()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from PIL import Image                                               # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


racine = pathlib.Path(__file__).resolve().parents[2]
vieux = subprocess.run(["git", "show", "09621e3:backend/app/services/post_preview.py"], cwd=racine, capture_output=True).stdout.decode("utf-8")
print("\n[0] témoin : la base 09621e3")
check("0.1 TÉMOIN : pas de SAFE_ZONES, tout canal inconnu tombait sur la carte X", vieux and "SAFE_ZONES" not in vieux and "_render_x(" in vieux)

from app.config import settings                                     # noqa: E402
settings.DATABASE_URL = os.environ["DATABASE_URL"]
settings.IMAGES_FOLDER = os.environ["IMAGES_FOLDER"]
from app.services import post_preview as PP                         # noqa: E402

hero = _tmp / "images" / "hero.png"
Image.new("RGB", (1080, 1920), (240, 240, 240)).save(hero)
large = _tmp / "images" / "paysage.png"
im = Image.new("RGB", (1920, 1080), (20, 20, 200))                  # bleu, avec des bords rouges qui doivent être rognés
for x in range(0, 300):
    for y in range(0, 1080, 4):
        im.putpixel((x, y), (255, 0, 0)); im.putpixel((1919 - x, y), (255, 0, 0))
im.save(large)


def lum(im, x, y):
    r, g, b = im.getpixel((x, y))[:3]
    return (r + g + b) / 3


def rendu(ch, h=hero, cap="Salut 🐙 légende"):
    return Image.open(io.BytesIO(PP.render_preview(channel=ch, caption=cap, hero_path=str(h) if h else None))).convert("RGB")


print("\n[1] les trois lecteurs verticaux")
for ch in ("instagram", "youtube", "tiktok"):
    im = rendu(ch)
    W, H = im.size
    z = PP.SAFE_ZONES[ch]
    coeur = lum(im, W // 2, int(H * (z["top"] + (1 - z["bottom"])) / 2))
    check(f"1.{ch} 540×960, bande haute + rail droit + bande basse assombris, cœur du visuel intact",
          (W, H) == (540, 960) and coeur > 200 and lum(im, W // 2, int(H * z["top"] / 2)) < coeur - 40
          and lum(im, W - 4, H // 2) < coeur - 40 and lum(im, 4, H - 4) < coeur - 40, f"{im.size} coeur={coeur}")
im = rendu("tiktok", cap="LÉGENDE BLANCHE")
W, H = im.size
z = PP.SAFE_ZONES["tiktok"]
bande = [im.getpixel((x, y)) for x in range(0, int(W * (1 - z["right"]))) for y in range(H - int(H * z["bottom"]), H)]
check("1.4 la légende est écrite DANS la bande basse (pixels presque blancs sur fond assombri)",
      sum(1 for p in bande if min(p) > 230) > 150, str(sum(1 for p in bande if min(p) > 230)))
vide = rendu("tiktok", cap="")
bande0 = [vide.getpixel((x, y)) for x in range(0, int(W * (1 - z["right"]))) for y in range(H - int(H * z["bottom"]) + 40, H)]
check("1.5 sans légende, la bande reste vide sous le nom (preuve que 1.4 mesure bien le texte)",
      sum(1 for p in bande0 if min(p) > 230) < 20, str(sum(1 for p in bande0 if min(p) > 230)))

print("\n[2] cadrage et absence de visuel")
p = rendu("youtube", h=large)
check("2.1 un visuel paysage est RECADRÉ (cover) : le centre est bleu, les bords rouges ont disparu",
      p.size == (540, 960) and p.getpixel((270, 480))[2] > 150 and p.getpixel((270, 480))[0] < 80
      and all(p.getpixel((30, y))[0] < 150 for y in range(200, 700, 50)), str(p.getpixel((270, 480))))
n = rendu("instagram", h=None)
check("2.2 sans visuel : un gabarit 9:16 (fond sombre), pas une carte X", n.size == (540, 960) and lum(n, 270, 300) < 90 and lum(n, 270, 700) < 90, str(n.size))

print("\n[3] X et Telegram inchangés")
check("3.1 X : la carte de 680 de large", rendu("x").size[0] == 680)
check("3.2 Telegram : sa bulle, pas un 540×960", rendu("telegram").size != (540, 960))
check("3.3 canal inconnu : toujours la carte X (comportement d'avant)", rendu("mastodon").size[0] == 680)

print("\n[4] la route")
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    pid = c.post("/api/schedule", json={"title": "t", "caption": "c", "channels": ["tiktok"],
                                        "run_at": "2026-09-10T10:00:00Z", "source_image": "hero.png"}).json()["id"]
    tailles = {}
    for ch in ("tiktok", "youtube", "instagram"):
        r = c.get(f"/api/schedule/{pid}/preview.png", params={"channel": ch})
        tailles[ch] = Image.open(io.BytesIO(r.content)).size if r.status_code == 200 else r.status_code
    check("4.1 /schedule/{id}/preview.png sert le 540×960 pour les trois canaux verticaux",
          set(tailles.values()) == {(540, 960)}, str(tailles))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
