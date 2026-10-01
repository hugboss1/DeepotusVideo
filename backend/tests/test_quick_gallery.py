# -*- coding: utf-8 -*-
"""Plan Quick T7 (tache #54 du suivi, D1, 01/10/2026) — la galerie de mouvements et de styles : 11 cameras x 3 styles
rendus UNE fois, LOCALEMENT, par ffmpeg, sur une image fixe. Le banc lit le PIXEL en mouvement (deux images extraites
de la meme vignette different pour « slow push-in », presque pas pour « static, locked-off »), les routes, et la
camera qui entre enfin dans un prompt LIBRE. Aucun reseau, aucun numpy, data-dir isole (aucune cle reelle).
Temoin positif : la base (80af191c) n'a ni quick_gallery ni la camera sur la branche du prompt libre.
Run (depuis backend/) : & $PY tests/test_quick_gallery.py"""
import json, os, pathlib, shutil, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzqgal_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from PIL import Image                                               # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "80af191c"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/prompt_engine.py"], capture_output=True, cwd=str(_ICI.parent))
pe0 = r0.stdout.decode("utf-8")
br0 = pe0[pe0.find("if request.custom_prompt:"):pe0.find("if not request.template_id:")]
r1 = subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/quick_gallery.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a pas quick_gallery", r1.returncode != 0)
check("T2 temoin : la base ignore la camera sur la branche du prompt libre", r0.returncode == 0 and br0 and "camera" not in br0)

from app.services import quick_gallery as G                         # noqa: E402
from app.services.effects_preview import ffmpeg_bin                 # noqa: E402
from app.models.schemas import CameraMove, StylePreset, GenerateRequest  # noqa: E402


def _source(nom, w=135, h=240, decal=0) -> pathlib.Path:
    """Damier contraste : du detail a deplacer, peint petit puis agrandi au plus proche voisin."""
    p = _tmp / "images" / nom
    petite = Image.new("RGB", (w, h)); px = petite.load()
    for y in range(h):
        for x in range(w):
            v = (x + y + decal) % 2
            px[x, y] = (20 + y % 200, 90 * v, 120 + x % 120)
    petite.resize((w * 8, h * 8), Image.NEAREST).save(p)
    return p


def _diff(video: pathlib.Path, t1: float, t2: float) -> float:
    ims = []
    for i, t in enumerate((t1, t2)):
        png = _tmp / f"{video.stem}_{i}.png"
        subprocess.run([ffmpeg_bin(), "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", str(png)],
                       check=True, timeout=120)
        ims.append(list(Image.open(png).convert("L").resize((90, 160)).getdata()))
    return sum(abs(a - b) for a, b in zip(*ims)) / float(len(ims[0]))


def _taille(video):
    r = subprocess.run([ffmpeg_bin(), "-i", str(video)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    import re
    m = re.search(r", (\d{2,5})x(\d{2,5})", r.stderr)
    return (int(m.group(1)), int(m.group(2))) if m else None


print("\n[M] le manifeste couvre le vocabulaire")
check("M1 onze cameras = CameraMove, trois styles = StylePreset",
      len(G.CAMERAS) == 11 and set(G.CAMERAS) == {c.value for c in CameraMove}
      and len(G.GRADES) == 3 and set(G.GRADES) == {c.value for c in StylePreset}, str(sorted(G.CAMERAS)))
check("M2 le nom d'une vignette ne sort pas du dossier", G.tile_path("../../x").parent == G.gallery_dir()
      and G.tile_path("../../x").name == "x.mp4")

print("\n[V] les vignettes bougent, ou ne bougent pas, comme annonce")
src = _source("marque.png")
t0 = time.time()
man = G.build(src, only=[("slow push-in", "cinematic"), ("static, locked-off", "cinematic"), ("crane shot descending", "ugc_raw")])
duree = time.time() - t0
par_cam = {t["camera"]: G.tile_path(t["id"]) for t in man["tiles"]}
check("V1 trois vignettes rendues, en mp4 9:16 540x960", len(man["tiles"]) == 3
      and all(p.is_file() for p in par_cam.values()) and _taille(par_cam["slow push-in"]) == (540, 960),
      f"{man} {_taille(par_cam.get('slow push-in', src))}")
bouge = _diff(par_cam["slow push-in"], 0.1, 1.8)
fixe = _diff(par_cam["static, locked-off"], 0.1, 1.8)
grue = _diff(par_cam["crane shot descending"], 0.1, 1.8)
check("V2 le push-in deplace des pixels, le plan fixe n'en deplace pas", bouge > 4.0 and fixe < 1.0 and bouge > fixe * 4,
      f"bouge={bouge:.2f} fixe={fixe:.2f}")
check("V3 la grue descend aussi (une autre expression que le zoom)", grue > 4.0, f"{grue:.2f}")
print(f"        ({duree:.1f} s pour trois vignettes)")
check("V4 le manifeste dit ce que la galerie N'EST PAS", "montrent le mot, pas le rendu du mod" in man.get("note", "")
      and json.loads(G.manifest_path().read_text("utf-8"))["n"] == 3)

print("\n[I] idempotence et image carree")
mt = {k: p.stat().st_mtime_ns for k, p in par_cam.items()}
G.build(src, only=[("slow push-in", "cinematic"), ("static, locked-off", "cinematic"), ("crane shot descending", "ugc_raw")])
check("I1 meme image : aucune vignette refaite", all(par_cam[k].stat().st_mtime_ns == v for k, v in mt.items()))
carre = _source("carree.png", 120, 120, decal=1)
man_c = G.build(carre, only=[("slow push-in", "cinematic")])
check("I2 autre image : la vignette est refaite, toujours 540x960 (recadree, pas deformee)",
      par_cam["slow push-in"].stat().st_mtime_ns != mt["slow push-in"] and _taille(par_cam["slow push-in"]) == (540, 960))
u_avant = [t["url"] for t in man["tiles"] if t["camera"] == "slow push-in"][0]
u_apres = man_c["tiles"][0]["url"]
# preuve ecran 01/10 : meme URL apres re-rendu = le navigateur rejouait l'ANCIENNE vignette depuis son cache
check("I5 autre image : l'URL de la vignette CHANGE (sinon le cache du navigateur montre l'ancienne) ; meme id",
      u_avant != u_apres and u_avant.split("?")[0] == u_apres.split("?")[0] and man_c["source_sha1"] in u_apres, f"{u_avant} {u_apres}")
blanc = _tmp / "images" / "carre_blanc.png"
im = Image.new("RGB", (800, 800), (0, 0, 0)); im.paste((255, 255, 255), (200, 200, 600, 600)); im.save(blanc)
G.build(blanc, only=[("static, locked-off", "cinematic")])
png = _tmp / "fixe0.png"
subprocess.run([ffmpeg_bin(), "-y", "-v", "error", "-ss", "0.5", "-i", str(G.tile_path(G.tile_id("static, locked-off", "cinematic"))),
                "-frames:v", "1", str(png)], check=True, timeout=120)
fr = Image.open(png).convert("L"); ligne = [fr.getpixel((x, fr.height // 2)) for x in range(fr.width)]
part = sum(1 for v in ligne if v > 128) / float(len(ligne))
check("I4 image carree RECADREE au centre, pas etiree : le carre blanc (1/2 du cote) couvre ~89 % de la largeur, pas 50 %",
      0.82 < part < 0.95, f"{part:.2f}")
try:
    G.build(_tmp / "images" / "absente.png"); e1 = None
except ValueError as e:
    e1 = str(e)
check("I3 image absente : ValueError lisible", e1 and "absente.png" in e1, str(e1))

print("\n[P] la camera entre dans un prompt LIBRE")
from app.services.prompt_engine import PromptEngine                 # noqa: E402
pe = PromptEngine()
pos, _neg = pe.build_prompt(GenerateRequest(image_filename="a.png", custom_prompt="un trone abyssal", camera=CameraMove.CRANE_DOWN))
check("P1 prompt libre + camera : la phrase est ajoutee", "un trone abyssal" in pos and "Camera: crane shot descending." in pos, pos)
pos2, _ = pe.build_prompt(GenerateRequest(image_filename="a.png", custom_prompt="un trone abyssal"))
check("P2 sans camera : le prompt libre est intact (aucune camera inventee)", "Camera:" not in pos2, pos2)
pos3, _ = pe.build_prompt(GenerateRequest(image_filename="a.png", custom_prompt="trone. Camera: crane shot descending.",
                                          camera=CameraMove.CRANE_DOWN))
check("P3 camera deja ecrite (par la galerie) : pas de doublon", pos3.count("Camera: crane shot descending.") == 1, pos3)

print("\n[R] les routes")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
for f in G.gallery_dir().iterdir():
    f.unlink()
G.CAMERAS = {k: G.CAMERAS[k] for k in ("slow push-in", "static, locked-off")}   # route = tout le dictionnaire : on l'abrege
G.GRADES = {"cinematic": G.GRADES["cinematic"]}
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    g0 = c.get("/api/quick/gallery").json()
    check("R1 jamais rendue : built:false + le vocabulaire", g0.get("built") is False and g0.get("cameras") == list(G.CAMERAS), str(g0))
    check("R2 sans image : 400 qui le dit", c.post("/api/quick/gallery/build", json={}).status_code == 400)
    check("R3 image inconnue : 404", c.post("/api/quick/gallery/build", json={"image": "nope.png"}).status_code == 404)
    check("R4 un chemin qui remonte est ramene a son nom (404, pas une lecture hors Library)",
          c.post("/api/quick/gallery/build", json={"image": "../t.db"}).status_code == 404)
    b = c.post("/api/quick/gallery/build", json={"image": "marque.png"})
    bj = b.json() if b.status_code == 200 else {}
    check("R5 build : 200, le manifeste (2 vignettes), source nommee", b.status_code == 200 and bj.get("n") == 2
          and bj.get("source") == "marque.png", b.text[:200])
    g1 = c.get("/api/quick/gallery").json()
    check("R6 relu : built:true + memes vignettes", g1.get("built") is True and [t["id"] for t in g1["tiles"]] == [t["id"] for t in bj["tiles"]])
    v = c.get(bj["tiles"][0]["url"]) if bj.get("tiles") else None
    check("R7 une vignette : 200 video/mp4, octets ftyp", v is not None and v.status_code == 200
          and v.headers.get("content-type", "").startswith("video/mp4") and v.content[4:8] == b"ftyp")
    check("R8 vignette inconnue : 404", c.get("/api/quick/gallery/000000000000").status_code == 404)

print(f"\n{ok} ok, {fail} fail")
shutil.rmtree(_tmp, ignore_errors=True)
sys.exit(1 if fail else 0)
