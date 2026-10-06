# -*- coding: utf-8 -*-
"""T103 (plan-son-vfx T10, D2b) — les effets se composent ENTRE le fond et le sujet détouré. Preuve par lecture de
pixels sur des rendus ffmpeg RÉELS du Montage (`_build_montage_command`) : fond bleu uni, sujet = une moitié rouge
opaque (ProRes 4444 avec alpha), effet = négatif (invert).
  · « derrière » (le défaut avec un matte) : le sujet reste rouge, le fond s'inverse (bleu → jaune) ;
  · « devant » : le sujet s'inverse aussi (rouge → cyan) ;
  · le matte SUIT le plan : même fenêtre de source (`src_in`) et même vitesse — le sujet qui change de côté à
    mi-source tombe au bon endroit du rendu (le plan du 03/09 ne prévoyait que -ss/-t : à ×2 il décalait) ;
  · sans matte, la commande est celle d'avant OCTET POUR OCTET ; avec un masque (D-30) le matte s'efface (le
    masque décide déjà où vont les effets), commande identique à « sans matte » ;
  · la vignette du rack respecte le matte ; un nom hostile est refusé ; `_resolve_src({matte})` est confiné.
Run: python tests/test_matte_compose.py (depuis backend/)"""
import asyncio, os, pathlib, shutil, subprocess, sys, tempfile
_tmp = tempfile.mkdtemp(prefix="dzcomp_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images")); pathlib.Path(_tmp, "images").mkdir()
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if not shutil.which("ffmpeg"):
    print("SKIP: ffmpeg introuvable"); sys.exit(0)
from loguru import logger
logger.remove()
from PIL import Image
from app.services import montage_service as M, matte_service as MT, effects_preview as FXP
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
def ff(*a): subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
w = pathlib.Path(_tmp); W, H, FPS = 64, 64, 10
ff("-f", "lavfi", "-i", f"color=c=0x0000ff:size={W}x{H}:rate={FPS}:duration=2", "-pix_fmt", "yuv420p", str(w / "bg.mp4"))

def matte(nom, cote_par_image):
    """Un sujet rouge opaque sur une moitié (« g » ou « d ») par image, transparent ailleurs."""
    fr = w / ("fr_" + nom); fr.mkdir()
    for i, c in enumerate(cote_par_image):
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        im.paste((255, 0, 0, 255), (0, 0, W // 2, H) if c == "g" else (W // 2, 0, W, H))
        im.save(fr / f"{i:03d}.png")
    mov = MT.mattes_dir() / f"{nom}.mov"
    ff("-framerate", str(FPS), "-i", str(fr / "%03d.png"), "-vf", "format=yuva444p10le",
       "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(mov))
    return mov
fixe = matte("sujet_fixe", ["g"] * 20)                  # 2 s, sujet à gauche
bascule = matte("sujet_bascule", ["g"] * 10 + ["d"] * 10)   # gauche la 1re seconde, droite la 2e

def px(video, t, x, y):
    out = w / "f.png"; ff("-ss", str(t), "-i", str(video), "-frames:v", "1", "-update", "1", str(out))
    return Image.open(out).convert("RGB").getpixel((x, y))
def seg(**kw):
    s = {"path": w / "bg.mp4", "src_dur": 2.0, "src_in": 0.0, "start": 0.0, "end": 1.0, "transition": "cut"}
    s.update(kw); return s
def cmd_de(v1, name):
    cmd, _ = M._build_montage_command(v1, [], [], None, w=W, h=H, fps=FPS,
                                      mix_db={"dialogue": -6, "musique": -18, "sfx": -12}, ducking=False,
                                      duration_master=False, preview=True, out=w / name)
    return cmd
def rend(v1, name):
    subprocess.run(cmd_de(v1, name), check=True, capture_output=True); return w / name
rouge = lambda p: p[0] > 190 and p[1] < 70 and p[2] < 70
bleu = lambda p: p[2] > 190 and p[0] < 70 and p[1] < 70
jaune = lambda p: p[0] > 190 and p[1] > 190 and p[2] < 70
cyan = lambda p: p[0] < 70 and p[1] > 190 and p[2] > 190

print("\n[1] derrière / devant / sans effet")
o = rend([seg(effects=[{"type": "invert", "behind": True}], matte=fixe)], "behind.mp4")
l, r_ = px(o, 0.5, 8, 32), px(o, 0.5, 56, 32)
check("derrière : sujet rouge intact, fond inversé (bleu → jaune)", rouge(l) and jaune(r_), f"{l} {r_}")
o = rend([seg(effects=[{"type": "invert"}], matte=fixe)], "defaut.mp4")
check("`behind` absent = derrière (la raison d'être du matte)", rouge(px(o, 0.5, 8, 32)) and jaune(px(o, 0.5, 56, 32)))
o = rend([seg(effects=[{"type": "invert", "behind": False}], matte=fixe)], "front.mp4")
l, r_ = px(o, 0.5, 8, 32), px(o, 0.5, 56, 32)
check("devant : sujet inversé aussi (rouge → cyan), fond jaune", cyan(l) and jaune(r_), f"{l} {r_}")
o = rend([seg(effects=[], matte=fixe)], "none.mp4")
l, r_ = px(o, 0.5, 8, 32), px(o, 0.5, 56, 32)
check("sans effet : sujet rouge sur fond bleu", rouge(l) and bleu(r_), f"{l} {r_}")

print("\n[2] le matte suit le plan")
o = rend([seg(src_in=1.0, end=0.8, effects=[{"type": "invert"}], matte=bascule)], "srcin.mp4")
l, r_ = px(o, 0.3, 8, 32), px(o, 0.3, 56, 32)
check("src_in 1,0 : on lit la 2e seconde du matte — sujet à DROITE", jaune(l) and rouge(r_), f"{l} {r_}")
o = rend([seg(speed=2.0, end=0.9, effects=[{"type": "invert"}], matte=bascule)], "vitesse.mp4")
l, r_ = px(o, 0.75, 8, 32), px(o, 0.75, 56, 32)
check("×2 : à 0,75 s de rendu on est à 1,5 s de source — sujet à DROITE (la vitesse s'applique au matte)",
      jaune(l) and rouge(r_), f"{l} {r_}")
l, r_ = px(o, 0.2, 8, 32), px(o, 0.2, 56, 32)
check("×2 : à 0,2 s de rendu (0,4 s de source) — sujet à GAUCHE", rouge(l) and jaune(r_), f"{l} {r_}")

dz = M._dz_spec({"dz": {"x0": 0.5, "y0": 0.25, "w0": 0.5, "x1": 0.5, "y1": 0.25, "w1": 0.5}})
o = rend([seg(dz=dz, effects=[{"type": "invert"}], matte=fixe)], "zoom.mp4")
l, r_ = px(o, 0.5, 8, 32), px(o, 0.5, 56, 32)
check("zoom dans la moitié DROITE (sans sujet) : le matte est zoomé avec la plaque — aucun rouge, tout jaune",
      dz is not None and jaune(l) and jaune(r_), f"{l} {r_}")

print("\n[3] ce qui ne change pas")
base = [seg(effects=[{"type": "invert"}])]
c0 = cmd_de(base, "h.mp4")
check("sans matte : aucun overlay, chaîne n0pre historique", "overlay" not in " ".join(c0) and "[n0pre]" in " ".join(c0))
check("matte None = pas de clé : commande identique octet pour octet",
      cmd_de([seg(effects=[{"type": "invert"}], matte=None)], "h.mp4") == c0)
masque = {"shape": "rect", "x": 0.0, "y": 0.0, "w": 0.5, "h": 1.0}
cm = cmd_de([seg(effects=[{"type": "invert"}], mask=M._mr.mask_of(masque))], "m.mp4")
cmm = cmd_de([seg(effects=[{"type": "invert"}], mask=M._mr.mask_of(masque), matte=fixe)], "m.mp4")
check("avec un masque : le matte s'efface (commande identique à « sans matte »)",
      M._mr.mask_of(masque) is not None and cmm == cm and str(fixe) not in " ".join(cmm))
check("matte sans effet sur un clip : composé quand même (le sujet reste devant un fond nu)",
      str(fixe) in " ".join(cmd_de([seg(effects=None, matte=fixe)], "x.mp4")))

print("\n[4] résolution confinée")
check("_resolve_src({matte}) : le .mov du dossier", asyncio.run(M._resolve_src({"matte": fixe.name})) == fixe.resolve())
for bad in ("../t.db", "absent.mov", "x.mp4", "../../bg.mp4", r"..\..\bg.mp4"):   # bg.mp4 EXISTE hors du dossier
    check(f"_resolve_src({{matte: {bad!r}}}) : None", asyncio.run(M._resolve_src({"matte": bad})) is None)

print("\n[5] la vignette du rack")
Image.new("RGB", (W, H), (0, 0, 255)).save(pathlib.Path(os.environ["IMAGES_FOLDER"]) / "bleu.png")
p = FXP.render_preview("invert", {}, source="image:bleu.png", matte=fixe.name, width=W)
im = Image.open(p).convert("RGB")
check("aperçu : sujet intact, fond inversé", rouge(im.getpixel((8, 32))) and jaune(im.getpixel((56, 32))),
      f"{im.getpixel((8, 32))} {im.getpixel((56, 32))}")
p0 = FXP.render_preview("invert", {}, source="image:bleu.png", width=W)
check("aperçu sans matte : tout inversé, autre fichier de cache", p0 != p and jaune(Image.open(p0).convert("RGB").getpixel((8, 32))))
for bad in ("../evil.mov", "absent.mov"):
    try: FXP.render_preview("invert", {}, source="image:bleu.png", matte=bad); check(f"matte {bad!r} refusé", False)
    except ValueError: check(f"matte {bad!r} refusé (ValueError)", True)
print("\n[6] les routes")
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.storage import init_db, async_session_factory, JobRecord
CAPT = []
_vrai_build = M._build_montage_command
def _capture(v1, *a, **k):
    CAPT.append([dict(s) for s in v1]); return _vrai_build(v1, *a, **k)
M._build_montage_command = _capture
async def routes():
    await init_db()
    async with async_session_factory() as s:
        s.add(JobRecord(id="job-c1", status="done", progress=100, image_filename="x", final_video_path=str(w / "bg.mp4")))
        await s.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient") as c:
        r = await c.get("/api/effects/preview", params={"type": "invert", "source": "image:bleu.png", "matte": fixe.name, "w": W})
        ok_img = r.status_code == 200
        if ok_img:
            (w / "route.jpg").write_bytes(r.content)
            im2 = Image.open(w / "route.jpg").convert("RGB")
        check("GET /effects/preview?matte= : sujet intact, fond inversé",
              ok_img and rouge(im2.getpixel((8, 32))) and jaune(im2.getpixel((56, 32))), str(r.status_code))
        r = await c.get("/api/effects/preview", params={"type": "invert", "source": "image:bleu.png", "matte": "../t.db"})
        check("GET /effects/preview?matte=hostile : 400", r.status_code == 400, str(r.status_code))
        clip = {"id": "c1", "tr": "v1", "src": {"job_id": "job-c1"}, "start": 0, "end": 1, "srcIn": 0,
                "effects": [{"type": "invert"}]}
        for matte_nom, attendu in ((fixe.name, fixe.resolve()), ("absent.mov", None)):
            CAPT.clear()
            await c.post("/api/montage/render", json={"preview": True, "clips": [dict(clip, matte=matte_nom)]})
            for _ in range(200):
                if CAPT: break
                await asyncio.sleep(0.05)
            vu = CAPT[0][0].get("matte") if CAPT else "rien"
            check(f"POST /montage/render : matte {matte_nom!r} -> le builder reçoit {attendu}",
                  vu == attendu, str(vu))
    # les rendus lancés en tâche de fond se TERMINENT avant la sortie du banc (sinon SQLAlchemy finalise
    # ses greenlets en pleine écriture du JobRecord : bruit à l'arrêt, cf. bancs-arret-isole)
    autres = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if autres:
        await asyncio.wait(autres, timeout=60)
asyncio.run(routes())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
