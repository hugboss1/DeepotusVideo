# -*- coding: utf-8 -*-
"""Son & VFX › Post-traitement (t276, 22/10/2026) — une PILE ordonnée de presets `effects_engine`, appliquée à un rendu
choisi (Bibliothèque › Rendus, résultat VFX IA, particules), aperçu avant/après à l'instant t, rendu ffmpeg local et
gratuit en job, rangé dans la Bibliothèque avec la relation « post ». Page `DzSvPost`, posée par le maillon de queue
`dzsonvfx` depuis sa source frontend/patches/sonvfx-post.js, après `/*__dzsvparticules*/`.
Sections :
  [C] catalogue : les 15 presets de post dans l'ordre, chacun sur un effet du moteur ; trois effets neufs
      (grain16, silverbw, duotone) au catalogue du rack, traduits ;
  [F] chaque preset compile ET rend 1 s sans erreur, à 30 % et à 100 % ;
  [V] la pile : validation, bornes, masquer, intensité nulle, ordre gardé, paramètres hostiles écartés, mélange
      dry/wet des effets sans intensité ;
  [A] aperçu et rendu : même graphe, l'image de l'aperçu à t = l'image du rendu à t, avant ≠ après, son gardé,
      durée gardée, source à alpha (particules) posée sur du noir ;
  [R] routes /api/post : catalogue, sources (rendus, VFX IA, particules), aperçu, rendu en job vers la Bibliothèque
      (relation « post », mère = la source), presets de pile enregistrés et supprimés, refus.
  [S] [H] [P] [K] : la page (source aplatie, hub, sous node, textes).
Run (depuis backend/) : & $PY tests/test_sonvfx_post.py"""
import asyncio, json, os, pathlib, re, shutil, subprocess, sys, tempfile

_tmp = tempfile.mkdtemp(prefix="dzpost276_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(RACINE / "backend"))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:700]}")


from loguru import logger  # noqa: E402
logger.remove()
from PIL import Image, ImageChops, ImageStat  # noqa: E402
from app.config import settings  # noqa: E402
from app.services import effects_engine as FX  # noqa: E402
try:
    from app.services import post_pile as PP  # noqa: E402
except Exception as _e:  # noqa: BLE001
    PP = None
    print(f"  (post_pile introuvable : {_e})")

W = pathlib.Path(_tmp)
FF = shutil.which("ffmpeg") or "ffmpeg"


def _ffmpeg(*args):
    subprocess.run([FF, "-y", "-v", "error", *args], check=True, capture_output=True, timeout=300)


def _ecart(a, b):
    """Écart moyen par canal entre deux images (0 = identiques)."""
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return 999.0
    return sum(ImageStat.Stat(ImageChops.difference(ia, ib)).mean) / 3.0


ORDRE = ["grain16", "bloom", "glitch_rgb", "aberration", "vignette", "halation", "lut", "vhs", "flou_mouvement",
         "nettete", "bandes", "tremblement", "fuite", "nb_argentique", "duotone"]

# ── [C] catalogue ─────────────────────────────────────────────────────────────────────────────────────────────────
print("[C] catalogue")
CAT = FX.catalog()
POST = getattr(FX, "POST_PILE", {})
check("C1 les 15 presets de post, dans l'ordre du plan", list(POST) == ORDRE, list(POST))
check("C2 chaque preset repose sur un effet du moteur (EFFECTS et catalogue du rack)",
      POST and all(v["type"] in FX.EFFECTS and v["type"] in CAT for v in POST.values()),
      [k for k, v in POST.items() if v.get("type") not in FX.EFFECTS])
_pc = (FX.post_catalogue() if hasattr(FX, "post_catalogue") else [])
check("C3 post_catalogue() : id, type, catégorie, intensité propre ou mélange, paramètres réglables bornés",
      [p["id"] for p in _pc] == ORDRE and all(set(p) >= {"id", "type", "cat", "intensite", "params", "bounds"}
                                              and "intensity" not in p["params"]
                                              and all(q in p["bounds"] for q in p["params"]) for p in _pc), _pc[:2])
_pcd = {p["id"]: p for p in _pc}
check("C4 intensité propre pour les effets qui en ont une ; mélange pour LUT et bandes",
      _pcd and _pcd["grain16"]["intensite"] is True and _pcd["lut"]["intensite"] is False
      and _pcd["bandes"]["intensite"] is False and _pcd["duotone"]["intensite"] is True,
      {k: v["intensite"] for k, v in _pcd.items()})
check("C5 réglables : LUT (fichier .cube + ambiance), duotone (deux couleurs), bandes (format), flou (angle)",
      _pcd and set(_pcd["lut"]["params"]) == {"preset", "file"} and set(_pcd["duotone"]["params"]) == {"c0", "c1"}
      and _pcd["bandes"]["params"] == ["ratio"] and _pcd["flou_mouvement"]["params"] == ["angle"])
check("C6 trois effets neufs au rack : grain16 et silverbw (Rétro), duotone (Stylisation), aide ≤ 90",
      all(t in CAT for t in ("grain16", "silverbw", "duotone")) and CAT["grain16"]["cat"] == "retro"
      and CAT["silverbw"]["cat"] == "retro" and CAT["duotone"]["cat"] == "stylisation"
      and all(0 < len(CAT[t]["hint"]) <= 90 for t in ("grain16", "silverbw", "duotone")))
check("C7 le comptage de l'étalonnage reste à 13 (aucun effet neuf n'y entre)",
      {c["id"]: c["count"] for c in FX.categories()}.get("etalonnage") == 13)
from app.i18n import _DICO  # noqa: E402
check("C8 noms et aides des effets neufs traduits (messages.json, fr = texte de la table)",
      all((_DICO.get(f"effets.{t}.{k}") or {}).get("en") and _DICO[f"effets.{t}.{k}"]["fr"] == CAT[t][c]
          for t in ("grain16", "silverbw", "duotone") for k, c in (("nom", "label"), ("aide", "hint"))))
_r = subprocess.run([sys.executable, "-I", str(RACINE / "scripts" / "i18n_l4_serveur.py"), "--check"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(RACINE))
check("C9 i18n_l4_serveur --check vert", _r.returncode == 0, (_r.stdout + _r.stderr)[-300:])

# ── sources de test ───────────────────────────────────────────────────────────────────────────────────────────────
SRC = W / "source.mp4"
_ffmpeg("-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=2", "-f", "lavfi", "-i", "sine=f=440:d=2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-c:a", "aac", "-shortest", str(SRC))
SEC = W / "une_seconde.mp4"
_ffmpeg("-f", "lavfi", "-i", "testsrc2=s=160x90:r=25:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(SEC))
ALPHA = W / "alpha.webm"
_ffmpeg("-f", "lavfi", "-i", "color=c=red:s=64x64:r=24:d=1,format=rgba,geq=r=255:g=255:b=255:a='255*between(X,16,47)*between(Y,16,47)'",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", str(ALPHA))

# ── [F] chaque preset compile et rend 1 s ─────────────────────────────────────────────────────────────────────────
print("[F] chaque preset rend 1 s")


def _rend_une_seconde(pid, inten):
    dest = W / f"f_{pid}_{inten}.mp4"
    PP.rendre(SEC, [{"preset": pid, "intensite": inten}], dest)
    return dest.is_file() and dest.stat().st_size > 1000 and abs(PP.infos(dest)["dur"] - 1.0) < 0.15


_kos = []
for _pid in ORDRE:
    for _inten in (30, 100):
        try:
            if not _rend_une_seconde(_pid, _inten):
                _kos.append((_pid, _inten, "sortie"))
        except Exception as e:  # noqa: BLE001
            _kos.append((_pid, _inten, f"{type(e).__name__}: {str(e)[-160:]}"))
check("F1 les 15 presets rendent 1 s sans erreur, à 30 % et à 100 %", PP is not None and not _kos, _kos[:4])
check("F2 la pile entière (15 maillons à la suite) rend 1 s",
      lambda: PP.rendre(SEC, [{"preset": p, "intensite": 60} for p in ORDRE],
                                                       W / "pile15.mp4") and (W / "pile15.mp4").stat().st_size > 1000)

# ── [V] la pile ───────────────────────────────────────────────────────────────────────────────────────────────────
print("[V] la pile")


def _leve(f):
    try:
        f()
    except ValueError:
        return True
    return False


check("V1 preset inconnu, pile qui n'est pas une liste, maillon qui n'est pas un objet : ValueError",
      lambda: _leve(lambda: PP.normaliser([{"preset": "nexistepas"}])) and _leve(lambda: PP.normaliser("x"))
      and _leve(lambda: PP.normaliser([3])))
check("V2 au plus PILE_MAX (24) maillons", lambda: PP.PILE_MAX == 24
      and _leve(lambda: PP.normaliser([{"preset": "vignette"}] * 25)) and len(PP.normaliser([{"preset": "vignette"}] * 24)) == 24)
check("V3 intensité ramenée dans 0-100 (défaut 60 si illisible), masque booléen",
      lambda: [m["intensite"] for m in PP.normaliser([{"preset": "vignette", "intensite": 150},
                                                      {"preset": "vignette", "intensite": -5},
                                                      {"preset": "vignette", "intensite": "x"},
                                                      {"preset": "vignette"}])] == [100, 0, 60, 60]
      and PP.normaliser([{"preset": "vignette", "masque": "oui"}])[0]["masque"] is True)
check("V4 un maillon masqué ou à 0 % ne rend rien ; l'ordre de la pile est celui des effets",
      lambda: [e["type"] for e in PP.effets([{"preset": "vignette"}, {"preset": "grain16", "masque": True},
                                             {"preset": "bloom", "intensite": 0}, {"preset": "aberration"},
                                             {"preset": "grain16"}])] == ["vignette", "chroma", "grain16"])
check("V5 l'intensité passe à l'effet qui en a une, au mélange pour les autres",
      lambda: PP.effets([{"preset": "vignette", "intensite": 35}])[0]["intensity"] == 35
      and PP.effets([{"preset": "bandes", "intensite": 40}])[0]["_mix"] == 40
      and "_mix" not in PP.effets([{"preset": "vignette", "intensite": 35}])[0])
check("V6 paramètres hostiles écartés (couleur injectée, LUT hors dossier, format hors liste), défauts du preset sinon",
      lambda: (lambda e: e["type"] == "duotone" and e["c0"] == "#1b1f4a" and e["c1"] == "#00ff00")(
          PP.effets([{"preset": "duotone", "params": {"c0": "#;[x]ab", "c1": "00ff00"}}])[0])
      and "file" not in PP.effets([{"preset": "lut", "params": {"file": "../../x.cube"}}])[0]
      and PP.effets([{"preset": "bandes", "params": {"ratio": "9;x"}}])[0]["ratio"] == "2.39")
_ch = (PP.chaine([{"preset": "vignette"}, {"preset": "grain16"}], "pin", "pout", {"w": 320, "h": 180, "fps": 25})
       if PP else [])
_txt = ";".join(_ch)
check("V7 chaîne : la vignette AVANT le grain, de [pin] à [pout]", _txt.startswith("[pin]") and _txt.endswith("[pout]")
      and 0 <= _txt.find("vignette=") < _txt.find("noise="), _txt[:300])
_mx = ";".join(PP.chaine([{"preset": "bandes", "intensite": 40}], "pin", "pout", {"w": 320, "h": 180, "fps": 25})) if PP else ""
check("V8 mélange dry/wet : split, effet, blend normal à 0.40 ; à 100 % l'effet seul", "split=2" in _mx
      and "all_mode=normal:all_opacity=0.40" in _mx
      and "blend" not in ";".join(PP.chaine([{"preset": "bandes", "intensite": 100}], "pin", "pout",
                                            {"w": 320, "h": 180, "fps": 25})), _mx)
check("V9 pile vide (ou tout masqué) : un simple passage", lambda: PP.chaine([], "pin", "pout", {"w": 2, "h": 2})
      == ["[pin]null[pout]"] and PP.chaine([{"preset": "vhs", "masque": True}], "pin", "pout", {"w": 2, "h": 2})
      == ["[pin]null[pout]"])

# ── [A] aperçu et rendu ───────────────────────────────────────────────────────────────────────────────────────────
print("[A] aperçu et rendu")
PILE = [{"preset": "duotone", "intensite": 90}, {"preset": "vignette", "intensite": 70},
        {"preset": "grain16", "intensite": 50}, {"preset": "bandes", "intensite": 100}]
check("A1 infos de la source : 320x180, 25 i/s, ~2 s, avec son", lambda: (lambda i: (i["w"], i["h"], i["fps"], i["audio"])
      == (320, 180, 25, True) and abs(i["dur"] - 2.0) < 0.15)(PP.infos(SRC)))
check("A2 aperçu et rendu partagent le MÊME filter_complex", lambda: (lambda a, b: a and a == b)(
    PP.commande_apercu(SRC, PILE, 1.0, W / "x.png")[PP.commande_apercu(SRC, PILE, 1.0, W / "x.png").index("-filter_complex") + 1],
    PP.commande_rendu(SRC, PILE, W / "x.mp4")[PP.commande_rendu(SRC, PILE, W / "x.mp4").index("-filter_complex") + 1]))
_ap = _av = _fr = None
try:
    _ap = PP.apercu(SRC, PILE, 1.0)
    _av = PP.apercu(SRC, [], 1.0)
    _out = W / "rendu.mp4"
    PP.rendre(SRC, PILE, _out)
    _fr = W / "rendu_t1.png"
    _ffmpeg("-i", str(_out), "-vf", "select=eq(n\\,25)", "-frames:v", "1", "-update", "1", str(_fr))
except Exception as e:  # noqa: BLE001
    print(f"  (aperçu/rendu : {type(e).__name__}: {str(e)[-300:]})")
check("A3 aperçu : une image PNG à la taille de la source", lambda: Image.open(_ap).size == (320, 180)
      and Image.open(_ap).format == "PNG")
check("A4 avant ≠ après (la pile change vraiment l'image)", lambda: _ecart(_ap, _av) > 12, _ap and _av and _ecart(_ap, _av))
check("A5 l'image de l'aperçu à t = l'image du rendu à t (écart du seul encodage)", lambda: _ecart(_ap, _fr) < 3.0,
      _ap and _fr and _ecart(_ap, _fr))
check("A6 l'image de « avant » à t = la source à t", lambda: (lambda s: _ffmpeg("-i", str(SRC), "-vf", "select=eq(n\\,25)",
      "-frames:v", "1", "-update", "1", str(s)) or _ecart(_av, s) < 0.5)(W / "src_t1.png"))
check("A7 le rendu garde la durée et le son de la source", lambda: (lambda i: abs(i["dur"] - 2.0) < 0.15 and i["audio"])(
    PP.infos(W / "rendu.mp4")))
check("A8 cache : le même aperçu demandé deux fois rend le même fichier sans relancer ffmpeg",
      lambda: PP.apercu(SRC, PILE, 1.0) == _ap)
check("A9 aperçu réduit pour l'écran : largeur bornée, effets calculés à la taille de la source puis réduits",
      lambda: Image.open(PP.apercu(SRC, PILE, 1.0, largeur=160)).size == (160, 90)
      and PP.commande_apercu(SRC, PILE, 1.0, W / "y.png", largeur=160)[
          PP.commande_apercu(SRC, PILE, 1.0, W / "y.png", largeur=160).index("-filter_complex") + 1].endswith("scale=160:-2[pa]"))
check("A10 instant hors de la source : ramené dans la durée", lambda: Image.open(PP.apercu(SRC, PILE, 99)).size == (320, 180))
check("A11 source à alpha (particules) : décodée en VP9 alpha, posée sur du noir",
      lambda: (lambda p: Image.open(p).convert("RGB").getpixel((2, 2)) == (0, 0, 0)
               and min(Image.open(p).convert("RGB").getpixel((32, 32))) > 200)(PP.apercu(ALPHA, [], 0.2)))

# ── [R] routes ────────────────────────────────────────────────────────────────────────────────────────────────────
print("[R] routes /api/post")
from httpx import AsyncClient, ASGITransport  # noqa: E402
from app.main import app  # noqa: E402
from app.services.storage import init_db, async_session_factory, JobRecord, LibraryAsset  # noqa: E402
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db())
FINAL = settings.outputs_path / "final"
FINAL.mkdir(parents=True, exist_ok=True)
shutil.copyfile(SRC, FINAL / "rendu_a.mp4")
shutil.copyfile(SRC, FINAL / "vfx_b.mp4")
PART = settings.outputs_path / "sprites" / "abcd1234"
PART.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ALPHA, PART / "alpha.webm")
Image.new("RGBA", (8, 8)).save(PART / "sheet.png")


async def _jobs():
    async with async_session_factory() as s:
        s.add(JobRecord(id="job-rendu", status="done", progress=100, title="Rendu A", image_filename="x",
                        final_video_path=str(FINAL / "rendu_a.mp4"), provider="kling"))
        s.add(JobRecord(id="job-vfx", status="done", progress=100, title="VFX B", image_filename="x",
                        final_video_path=str(FINAL / "vfx_b.mp4"), provider="vfx_ia"))
        s.add(JobRecord(id="job-parti", status="done", progress=100, title="Particules · feu", image_filename="sheet.png",
                        final_video_path=str(PART / "sheet.png"), provider="sprite2d",
                        cost_meta=json.dumps({"kind": "particles", "webm": True})))
        s.add(JobRecord(id="job-sprite", status="done", progress=100, title="Sprite", image_filename="sheet.png",
                        final_video_path=str(PART / "sheet.png"), provider="sprite2d",
                        cost_meta=json.dumps({"kind": "sprite", "webm": False})))
        s.add(JobRecord(id="job-encours", status="generating_video", progress=10, title="En cours", image_filename="x",
                        provider="kling"))
        await s.commit()


loop.run_until_complete(_jobs())
RES = {}


async def _routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
        RES["cat"] = await c.get("/api/post/catalogue")
        RES["cat_en"] = await c.get("/api/post/catalogue", headers={"Accept-Language": "en-US,en;q=0.9"})
        RES["src"] = await c.get("/api/post/sources")
        RES["ap"] = await c.post("/api/post/apercu", json={"source": "job-rendu", "pile": PILE, "t": 1.0})
        RES["ap_avant"] = await c.post("/api/post/apercu", json={"source": "job-rendu", "pile": [], "t": 1.0})
        RES["ap_parti"] = await c.post("/api/post/apercu", json={"source": "job-parti", "pile": [], "t": 0.2})
        RES["ap_inconnu"] = await c.post("/api/post/apercu", json={"source": "job-absent", "pile": []})
        RES["ap_hostile"] = await c.post("/api/post/apercu", json={"source": "../x", "pile": []})
        RES["ap_encours"] = await c.post("/api/post/apercu", json={"source": "job-encours", "pile": []})
        RES["ap_sprite"] = await c.post("/api/post/apercu", json={"source": "job-sprite", "pile": []})
        RES["ap_preset"] = await c.post("/api/post/apercu", json={"source": "job-rendu", "pile": [{"preset": "zzz"}]})
        RES["rd"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "pile": PILE, "titre": "Ma pile"})
        RES["rd_vide"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "pile": [{"preset": "vhs", "masque": True}]})
        jid = (RES["rd"].json() or {}).get("job_id")
        for _ in range(240):
            j = await c.get(f"/api/jobs/{jid}")
            RES["job"] = j.json()
            if RES["job"].get("status") in ("done", "failed"):
                break
            await asyncio.sleep(0.25)
        _cube = "TITLE \"chaud\"\nLUT_3D_SIZE 2\n" + "\n".join(
            f"{min(1, r + 0.3)} {g * 0.8} {b * 0.5}" for b in (0, 1) for g in (0, 1) for r in (0, 1))
        RES["lut"] = await c.post("/api/post/lut", files={"fichier": ("Chaud film.cube", _cube.encode(), "text/plain")})
        RES["lut_ext"] = await c.post("/api/post/lut", files={"fichier": ("x.png", b"LUT_3D_SIZE 2", "image/png")})
        RES["lut_1d"] = await c.post("/api/post/lut", files={"fichier": ("x.cube", b"LUT_1D_SIZE 2", "text/plain")})
        RES["lut_nom"] = await c.post("/api/post/lut", files={"fichier": ("../../evil.cube", _cube.encode(), "text/plain")})
        RES["cat2"] = await c.get("/api/post/catalogue")
        RES["ap_lut"] = await c.post("/api/post/apercu", json={"source": "job-rendu", "t": 1.0, "pile": [
            {"preset": "lut", "intensite": 100, "params": {"file": "Chaud_film.cube"}}]})
        RES["pr0"] = await c.get("/api/post/presets")
        RES["pr_add"] = await c.post("/api/post/presets", json={"nom": "Pellicule chaude", "pile": PILE})
        RES["pr_mal"] = await c.post("/api/post/presets", json={"nom": "", "pile": PILE})
        RES["pr_mal2"] = await c.post("/api/post/presets", json={"nom": "X", "pile": [{"preset": "zzz"}]})
        RES["pr1"] = await c.get("/api/post/presets")
        pid = (RES["pr_add"].json() or {}).get("id", "x")
        RES["pr_del"] = await c.delete(f"/api/post/presets/{pid}")
        RES["pr_del404"] = await c.delete("/api/post/presets/nexistepas")
        RES["pr2"] = await c.get("/api/post/presets")
    async with AsyncClient(transport=ASGITransport(app=app, client=("192.168.1.20", 5000)), base_url="http://192.168.1.5") as c:
        RES["reseau"] = await c.post("/api/post/rendre", json={"source": "job-rendu", "pile": PILE})


try:
    loop.run_until_complete(_routes())
except Exception as e:  # noqa: BLE001
    print(f"  (routes : {type(e).__name__}: {e})")


def _j(k):
    r = RES.get(k)
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return None


check("R1 GET /catalogue : les 15 presets dans l'ordre, bornes, LUT disponibles",
      RES.get("cat") is not None and RES["cat"].status_code == 200
      and [p["id"] for p in _j("cat")["presets"]] == ORDRE and isinstance(_j("cat").get("luts"), list))
check("R2 catalogue en anglais : mêmes ids et bornes (libellés de paramètres traduits)",
      RES.get("cat_en") is not None and [p["id"] for p in _j("cat_en")["presets"]] == ORDRE
      and _j("cat_en")["presets"][ORDRE.index("duotone")]["bounds"]["c0"]["label"] == "Color 1"
      and _j("cat")["presets"][ORDRE.index("duotone")]["bounds"]["c0"]["label"] == "Couleur 1")
_s = _j("src") or {}
check("R3 GET /sources : Rendus (tous les rendus vidéo finis), VFX IA (provider vfx_ia), Particules (webm des jobs particules)",
      [x["job_id"] for x in _s.get("vfx", [])] == ["job-vfx"]
      and [x["job_id"] for x in _s.get("particules", [])] == ["job-parti"]
      and set(x["job_id"] for x in _s.get("rendus", [])) == {"job-rendu", "job-vfx"}, _s)
check("R4 une source porte job_id, titre, durée, dimensions", all(set(x) >= {"job_id", "titre", "dur", "w", "h"}
      for x in _s.get("rendus", []) + _s.get("particules", [])) and _s["particules"][0]["alpha"] is True, _s)
check("R5 POST /apercu : PNG, avant ≠ après", RES.get("ap") is not None and RES["ap"].status_code == 200
      and RES["ap"].headers.get("content-type") == "image/png" and RES["ap"].content != RES["ap_avant"].content,
      RES.get("ap") is not None and RES["ap"].text[:200])
check("R6 aperçu d'une source particules (webm alpha)", RES.get("ap_parti") is not None and RES["ap_parti"].status_code == 200)
check("R7 refus : job inconnu 404, id hostile 400, job pas fini 409, sprite sans vidéo 404, preset inconnu 400",
      [RES[k].status_code for k in ("ap_inconnu", "ap_hostile", "ap_encours", "ap_sprite", "ap_preset")]
      == [404, 400, 409, 404, 400], [RES[k].status_code for k in ("ap_inconnu", "ap_hostile", "ap_encours", "ap_sprite", "ap_preset") if k in RES])
check("R8 POST /rendre : un job, gratuit (usd 0)", RES.get("rd") is not None and RES["rd"].status_code == 200
      and _j("rd").get("job_id") and _j("rd").get("usd") == 0, RES.get("rd") is not None and RES["rd"].text[:300])
_job = RES.get("job") or {}
check("R9 le job finit : vidéo dans outputs/final, provider « post », titre donné",
      _job.get("status") == "done" and _job.get("provider") == "post" and _job.get("title") == "Ma pile"
      and pathlib.Path(_job.get("final_video_path") or "x").is_file()
      and pathlib.Path(_job["final_video_path"]).parent == FINAL, _job)


async def _lignee():
    async with async_session_factory() as s:
        return await s.get(LibraryAsset, pathlib.Path(_job.get("final_video_path") or "x").name)


_la = loop.run_until_complete(_lignee()) if _job.get("final_video_path") else None
check("R10 Bibliothèque : source sonvfx, vidéo, relation « post », mère = la source, recette = la pile",
      _la is not None and _la.source == "sonvfx" and _la.kind == "video" and _la.relation == "post"
      and _la.parent_filename == "rendu_a.mp4" and json.loads(_la.recette or "{}").get("pile")
      and _la.job_id == _job.get("job_id"), _la and vars(_la))
check("R11 rendre une pile qui ne rend rien : 400", RES.get("rd_vide") is not None and RES["rd_vide"].status_code == 400)
check("R12 presets de pile : liste vide, ajout, refus (nom vide, preset inconnu), suppression, 404",
      _j("pr0") == {"presets": []} and RES["pr_add"].status_code == 200 and _j("pr_add").get("nom") == "Pellicule chaude"
      and RES["pr_mal"].status_code == 400 and RES["pr_mal2"].status_code == 400
      and [p["nom"] for p in _j("pr1")["presets"]] == ["Pellicule chaude"]
      and [m["preset"] for m in _j("pr1")["presets"][0]["pile"]] == [m["preset"] for m in PILE]
      and RES["pr_del"].status_code == 200 and RES["pr_del404"].status_code == 404 and _j("pr2") == {"presets": []},
      [(k, RES[k].status_code) for k in ("pr0", "pr_add", "pr_mal", "pr_mal2", "pr1", "pr_del", "pr_del404") if k in RES])
check("R13 depuis le réseau : écriture refusée", RES.get("reseau") is not None and RES["reseau"].status_code in (401, 403))
check("R15 import d'une LUT .cube : rangée dans le dossier des LUT, nom assaini, listée, appliquée ; refus (extension, 1D)",
      RES.get("lut") is not None and RES["lut"].status_code == 200 and _j("lut")["nom"] == "Chaud_film.cube"
      and (settings.luts_path / "Chaud_film.cube").is_file() and "Chaud_film.cube" in _j("cat2")["luts"]
      and RES["lut_ext"].status_code == 400 and RES["lut_1d"].status_code == 400
      and _j("lut_nom")["nom"] == "evil.cube" and (settings.luts_path / "evil.cube").is_file()
      and RES["ap_lut"].status_code == 200 and RES["ap_lut"].content != RES["ap_avant"].content,
      [(k, RES[k].status_code) for k in ("lut", "lut_ext", "lut_1d", "lut_nom", "ap_lut") if k in RES])
check("R14 presets gardés dans le dossier des données (survivent aux mises à jour)",
      lambda: PP.presets_fichier().parent.resolve() == settings.outputs_path.parent.resolve())

# ── [S] [H] [P] [K] la page ───────────────────────────────────────────────────────────────────────────────────────
BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")
SRCJ_P = RACINE / "frontend" / "patches" / "sonvfx-post.js"
SRCJ = SRCJ_P.read_bytes().decode("utf-8")
_i, _j = BUNDLE.find("/*__dzsvparticules*/"), BUNDLE.find("/*__dzsvpost*/")
PAGE = BUNDLE[_i + len("/*__dzsvparticules*/"):_j] if 0 <= _i < _j else ""
_h0, _h1 = BUNDLE.find("var __dzSvHue="), BUNDLE.find("/*__dzsonvfx*/")
HUB = BUNDLE[_h0:_h1] if 0 <= _h0 < _h1 else ""

print("[S] source et livré")
import patch_bundle_dzsonvfx as PSV  # noqa: E402
check("S1 le livré porte la source aplatie, à l'octet", PAGE and PAGE == PSV.aplatir(SRCJ), (len(PAGE), len(PSV.aplatir(SRCJ))))
check("S2 la page est posée une fois, après les Particules et avant « const Te= »",
      BUNDLE.count("function DzSvPost(") == 1 and 0 < _i < _j < BUNDLE.find('const Te="/api";'))
_lignes, _dans = [], False
for _l in (l.strip() for l in SRCJ.splitlines()):
    if _dans or _l.startswith("/*"):
        _dans = not _l.endswith("*/")
        continue
    _lignes.append(_l)
check("S3 règles d'écriture : ni « // », ni ligne qui commence par ( ou [",
      not any(l.startswith(("//", "(", "[")) for l in _lignes), [l[:50] for l in _lignes if l.startswith(("//", "(", "["))])
check("S4 aucun texte en dur : libellés par dzT, aucun aria-label/placeholder/title/alt littéral",
      PAGE and not re.search(r'children:"[^"]*[A-Za-zÀ-ÿ]', PAGE)
      and not re.search(r'"aria-label":"|placeholder:"|title:"|alt:"', PAGE))
check("S5 clés dzT littérales seulement (aucune clé construite)", PAGE and not re.search(r'dzT\("[a-z0-9_.]+"\s*\+', PAGE))
_ROUTES = ('"/api/post/catalogue"', '"/api/post/sources"', '"/api/post/presets"', '"/api/post/apercu"',
           '"/api/post/rendre"', '"/api/post/lut"', '"/api/post/presets/"', '"/api/jobs/"')
check("S6 routes : catalogue, sources, presets, aperçu, rendu, LUT, suivi du job", PAGE and all(u in PAGE for u in _ROUTES),
      [u for u in _ROUTES if u not in PAGE])
_pr = (RACINE / "backend" / "app" / "api" / "post_routes.py").read_text(encoding="utf-8")
check("S7 chaque route /api/post appelée existe côté serveur",
      # t277 : /rendre porte la garde des dépenses en dépendance du décorateur (@router.post("/rendre", dependencies=…))
      all(re.search(rf'@router\.{m}\("{re.escape(u)}"[,)]', _pr) for m, u in (("get", "/catalogue"), ("get", "/sources"), ("get", "/presets"),
                                                    ("post", "/apercu"), ("post", "/rendre"), ("post", "/lut"),
                                                    ("post", "/presets"), ("delete", "/presets/{pid}"))))
check("S8 hooks par alias dans la fonction (x.useState( absent de la page)",
      "var US=x.useState,UE=x.useEffect,UR=x.useRef;" in PAGE and "x.useState(" not in PAGE)
check("S9 aucun arrondi : ni la page ni sa feuille ne posent de border-radius",
      PAGE and "border-radius" not in PAGE and "borderRadius" not in PAGE
      and "border-radius" not in getattr(PSV, "CSS_POST", "border-radius"))
_spr = (RACINE / "frontend" / "dist" / "shared" / "icons" / "dz-icons.svg").read_text(encoding="utf-8")
_gl = sorted(set(re.findall(r'"(dz-[a-z0-9-]+)"', SRCJ)))
check("S10 chaque glyphe Deepotus de la page existe dans le sprite", _gl and all(f'id="{g}"' in _spr for g in _gl),
      [g for g in _gl if f'id="{g}"' not in _spr])
check("S11 aucune confirmation par le dialogue global (compte figé ×30) : la suppression s'arme au premier clic",
      "__dzDialogue" not in PAGE and '"data-arme":arme?"":void 0' in PAGE)

print("[H] le hub")
check("H1 le Post-traitement rend DzSvPost (go transmis), la vue d'origine masquée par le même style",
      'post=sub==="post"' in HUB and re.search(r'style:pistes\|\|atelier\|\|voix\|\|parti\|\|post\?\{display:"none"\}:void 0', HUB)
      and 'post?r.jsx(DzSvPost,{go:p.go},"post"):null' in HUB)
check("H2 la feuille de la page est injectée avec celle du hub", ".dzsvo{" in HUB and ".dzsvo-comparer{" in HUB)

HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");
const i=S.indexOf("/*__dzsvparticules*/"),j=S.indexOf("/*__dzsvpost*/");if(i<0||j<i)throw new Error("page introuvable");
const CODE=S.slice(i,j);
let H=[],HI=0,EFF=[],CLEAN={};
const x={useState(v){const k=HI++;if(!(k in H))H[k]=typeof v==="function"?v():v;return [H[k],n=>{H[k]=typeof n==="function"?n(H[k]):n}]},
 useEffect(f,d){const k=HI++;const p=H[k];if(!p||!d||d.some((v,q)=>v!==p.d[q]))EFF.push([k,f]);H[k]={d:d||[]}},
 useRef(v){const k=HI++;if(!(k in H))H[k]={current:v};return H[k]}};
const r={jsx:(t,p,k)=>({t,p,k}),jsxs:(t,p,k)=>({t,p,k}),Fragment:"F"};
function dzT(k,v){return "⟦"+k+"⟧"+(v?JSON.stringify(v):"")}
function __dzGl(n){return {t:"glyph",p:{name:n}}}
function dzSvpJson(res){return res.json().catch(()=>({})).then(d=>{if(!res.ok){const m=d&&d.detail;throw new Error((typeof m==="string"&&m)||("code "+res.status))}return d})}
let MINUT=[];function setTimeout(f){MINUT.push(f);return MINUT.length}function clearTimeout(h){if(h>0&&h<=MINUT.length)MINUT[h-1]=null}
function minuteries(){const m=MINUT;MINUT=[];m.forEach(f=>f&&f())}
let NB=0,REVOQ=[];const URL={createObjectURL:b=>"blob:"+(++NB)+":"+b.tag,revokeObjectURL:u=>REVOQ.push(u)};
class FormData{constructor(){this.e=[]}append(k,v){this.e.push([k,v&&v.name])}}
let APPELS=[],CAT={},SRCS={},PRESETS=[],JOB={status:"generating_video",progress:40},REP={},NP=0,RETENIR=false,ATTENTE=[];
function json(d,st){return Promise.resolve({ok:(st||200)<400,status:st||200,json:()=>Promise.resolve(d),blob:()=>Promise.resolve({tag:"x"})})}
function fetch(u,o){o=o||{};const corps=o.body instanceof FormData?o.body.e:(o.body?JSON.parse(o.body):null);APPELS.push([u,o.method||"GET",corps]);
 if(REP[u])return json(REP[u].d,REP[u].st);
 if(u==="/api/post/catalogue")return json(CAT);
 if(u==="/api/post/sources")return json(SRCS);
 if(u==="/api/post/presets"&&(o.method||"GET")==="GET")return json({presets:PRESETS.slice()});
 if(u==="/api/post/presets"){NP++;return json({id:"pz"+NP,nom:corps.nom,pile:corps.pile,cree:1})}
 if(u.startsWith("/api/post/presets/"))return json({ok:true});
 if(u==="/api/post/apercu"&&RETENIR)return new Promise(ok=>ATTENTE.push(()=>ok({ok:true,status:200,json:()=>Promise.resolve({}),blob:()=>Promise.resolve({tag:"t"+corps.t+(corps.pile.length?"apres":"avant")})})));
 if(u==="/api/post/apercu")return Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({}),blob:()=>Promise.resolve({tag:corps.pile.length?"apres":"avant"})});
 if(u==="/api/post/rendre")return json({job_id:"jpost1",status:"queued",usd:0});
 if(u==="/api/post/lut")return json({nom:"Chaud.cube",luts:["Chaud.cube","Froid.cube"]});
 if(u.startsWith("/api/jobs/"))return json(Object.assign({job_id:"jpost1"},JOB));
 return json({},404)}
eval(CODE);
let ALLER=[];
function tout(n,f,acc){if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(c=>tout(c,f,acc));return acc}
 if(f(n))acc.push(n);if(n.p)tout(n.p.children,f,acc);return acc}
function texte(n){if(n==null||n===false)return "";if(typeof n==="string"||typeof n==="number")return String(n);
 if(Array.isArray(n))return n.map(texte).join("");if(n.t==="glyph")return "";return n.p?texte(n.p.children):""}
let A=null;
function rendre(){HI=0;EFF=[];A=DzSvPost({go:v=>ALLER.push(v)});const e=EFF;EFF=[];
 e.forEach(([k,f])=>{if(CLEAN[k])CLEAN[k]();const c=f();CLEAN[k]=typeof c==="function"?c:null});return A}
async function calme(){for(let k=0;k<10;k++){await new Promise(r0=>setImmediate(r0));rendre()}}
async function tic(){minuteries();await calme()}
function un(f){return tout(A,f,[])[0]}
function sp(a){return un(n=>n.p&&n.p["data-sv-post"]===a)}
function tous(a){return tout(A,n=>n.p&&n.p["data-sv-post"]===a,[])}
function pile(){return tous("maillon").map(m=>[m.p["data-preset"],m.p["data-masque"]])}
function maillon(k){return tous("maillon")[k]}
function dans(m,a){return tout(m,n=>n.p&&n.p["data-sv-post"]===a,[])[0]}
function apercus(){return APPELS.filter(a=>a[0]==="/api/post/apercu").map(a=>a[2])}
CAT={pile_max:4,luts:["Froid.cube"],presets:[
 {id:"grain16",type:"grain16",cat:"retro",intensite:true,defaut:55,params:[],bounds:{}},
 {id:"vignette",type:"vignette",cat:"lumiere",intensite:true,defaut:60,params:[],bounds:{}},
 {id:"lut",type:"grade",cat:"etalonnage",intensite:false,defaut:100,params:["preset","file"],bounds:{
   preset:{type:"choice",choices:["teal_orange","cyberpunk"],default:"teal_orange",label:"Préréglage"},file:{type:"lut",default:"",label:"LUT .cube"}}},
 {id:"duotone",type:"duotone",cat:"stylisation",intensite:true,defaut:100,params:["c0","c1"],bounds:{
   c0:{type:"color",default:"#1b1f4a",label:"Couleur 1"},c1:{type:"color",default:"#ffb36b",label:"Couleur 2"}}},
 {id:"flou_mouvement",type:"dirblur",cat:"mouvement",intensite:true,defaut:55,params:["angle"],bounds:{angle:{type:"range",min:0,max:360,step:1,default:0,label:"Angle",unit:"°"}}}]};
SRCS={rendus:[{job_id:"jA",titre:"Rendu A",dur:2,w:320,h:180,alpha:false},{job_id:"jB",titre:"VFX B",dur:4,w:1080,h:1920,alpha:false}],
 vfx:[{job_id:"jB",titre:"VFX B",dur:4,w:1080,h:1920,alpha:false}],particules:[]};
PRESETS=[{id:"pa",nom:"Ancienne",pile:[{preset:"vignette",intensite:20,masque:false,params:{}},{preset:"inconnu",intensite:5,masque:false,params:{}}]}];
const R={};
(async()=>{
rendre();R.attente=texte(A);await calme();
R.montage={appels:APPELS.map(a=>a[0]),familles:["rendus","vfx","particules"].map(f=>[texte(sp("famille-"+f)),sp("famille-"+f).p["aria-pressed"]]),
 srcs:tous("src-jA").length+tous("src-jB").length,attente:texte(sp("attente")),ajouts:CAT.presets.map(q=>!!sp("ajout-"+q.id)),
 pile_vide:!!sp("pile-vide"),rendre_off:sp("rendre").p.disabled,apercus:apercus().length};
sp("famille-particules").p.onClick();rendre();R.vide=!!sp("src-vide");
sp("famille-vfx").p.onClick();rendre();R.vfx=tous("src-jB").length+":"+tous("src-jA").length;
sp("famille-rendus").p.onClick();rendre();
sp("src-jA").p.onClick();rendre();rendre();R.calcul_avant_delai={calc:!!sp("calcul"),apercus:apercus().length,on:sp("src-jA").p["aria-pressed"]};
await tic();
R.apercu1={corps:apercus(),avant:sp("avant")&&sp("avant").p.src,apres:sp("apres")&&sp("apres").p.src,clip:sp("apres")&&sp("apres").p.style.clipPath,
 calc:!!sp("calcul"),instant:[sp("instant").p.max,sp("instant").p.step],ratio:un(n=>n.p&&n.p.className==="dzsvo-comparer").p.style.aspectRatio};
sp("curseur").p.onChange({target:{value:"30"}});rendre();R.clip30=sp("apres").p.style.clipPath;
APPELS=[];sp("instant").p.onChange({target:{value:"1.2"}});rendre();await tic();R.instant=apercus().map(c=>c.t);R.revoq=REVOQ.length;
APPELS=[];sp("ajout-grain16").p.onClick();rendre();sp("ajout-lut").p.onClick();rendre();
R.ajout={pile:pile(),deplie:[dans(maillon(0),"deplier").p["aria-expanded"],dans(maillon(1),"deplier").p["aria-expanded"]],
 inten:[dans(maillon(0),"intensite").p.value,dans(maillon(1),"intensite").p.value],noms:tous("deplier").map(texte),
 lut_reglages:[!!dans(maillon(1),"param-preset"),!!dans(maillon(1),"param-file")],rendre_off:sp("rendre").p.disabled};
await tic();R.apercu_pile=apercus().map(c=>c.pile);
dans(maillon(0),"intensite").p.onChange({target:{value:"80"}});rendre();
dans(maillon(1),"param-preset").p.onChange({target:{value:"cyberpunk"}});rendre();
R.lut_options=texte(dans(maillon(1),"param-file"));
APPELS=[];dans(maillon(1),"lut-import").p.onChange({target:{files:[{name:"Chaud.cube"}],value:"x"}});await calme();
R.lut_import={appel:APPELS[0],file:dans(maillon(1),"param-file").p.value,options:texte(dans(maillon(1),"param-file"))};
APPELS=[];await tic();R.apercu_regle=apercus().map(c=>c.pile);
dans(maillon(0),"masquer").p.onClick();rendre();R.masque={pile:pile(),pressed:dans(maillon(0),"masquer").p["aria-pressed"],lbl:dans(maillon(0),"masquer").p["aria-label"]};
dans(maillon(1),"masquer").p.onClick();rendre();R.tout_masque=sp("rendre").p.disabled;dans(maillon(1),"masquer").p.onClick();rendre();
dans(maillon(0),"dupliquer").p.onClick();rendre();R.dup={pile:pile(),inten:tous("intensite").map(m=>m.p.value)};
dans(maillon(2),"monter").p.onClick();rendre();R.monter=pile();
R.bornes=[dans(maillon(0),"monter").p.disabled,dans(maillon(2),"descendre").p.disabled];
dans(maillon(0),"descendre").p.onClick();rendre();R.descendre=pile();
const dt={effectAllowed:"",d:null,setData(a,b){this.d=b}};let pv=0;
maillon(2).p.onDragStart({dataTransfer:dt});maillon(0).p.onDragOver({preventDefault(){pv++}});maillon(0).p.onDrop({preventDefault(){pv++}});rendre();
R.glisser={pile:pile(),pv,d:dt.d,dr:maillon(0).p.draggable};
sp("ajout-duotone").p.onClick();rendre();R.plein={n:pile().length,off:CAT.presets.map(q=>sp("ajout-"+q.id).p.disabled),dup:dans(maillon(0),"dupliquer").p.disabled};
dans(maillon(3),"param-c0").p.onChange({target:{value:"#112233"}});rendre();
dans(maillon(3),"supprimer").p.onClick();rendre();R.suppr=pile();
sp("preset-nom").p.onChange({target:{value:"  Chaud  "}});rendre();R.enreg_on=!sp("preset-enreg").p.disabled;
APPELS=[];sp("preset-enreg").p.onClick();await calme();
R.enreg={appel:APPELS[0],choix:texte(sp("preset-choix")),sel:sp("preset-choix").p.value,nom:sp("preset-nom").p.value};
sp("preset-choix").p.onChange({target:{value:"pa"}});rendre();R.charge={pile:pile(),inten:tous("intensite").map(m=>m.p.value)};
APPELS=[];sp("preset-suppr").p.onClick();rendre();R.arme={appels:APPELS.length,arme:sp("preset-suppr").p["data-arme"]!==undefined,lbl:sp("preset-suppr").p["aria-label"]};
sp("preset-suppr").p.onClick();await calme();R.suppr_preset={appel:APPELS[0],choix:texte(sp("preset-choix"))};
sp("vider").p.onClick();rendre();R.videe=[pile().length,!!sp("pile-vide"),sp("rendre").p.disabled];
sp("ajout-vignette").p.onClick();rendre();
sp("rendu-titre").p.onChange({target:{value:" Ma pile "}});rendre();
APPELS=[];sp("rendre").p.onClick();await calme();
R.rendu={appel:APPELS[0],job:texte(sp("job")),off:sp("rendre").p.disabled};
await tic();R.suivi={appel:APPELS.find(a=>a[0].startsWith("/api/jobs/")),job:texte(sp("job"))};
JOB={status:"done",progress:100};APPELS=[];await tic();
R.fini={job:texte(sp("job")),sources:APPELS.some(a=>a[0]==="/api/post/sources"),montage:!!sp("montage"),off:sp("rendre").p.disabled};
sp("montage").p.onClick();R.aller=ALLER.slice();
APPELS=[];await tic();R.plus_de_suivi=APPELS.filter(a=>a[0].startsWith("/api/jobs/")).length;
REP["/api/post/apercu"]={d:{detail:"preset de post-traitement inconnu"},st:400};
sp("ajout-grain16").p.onClick();rendre();await tic();R.erreur=texte(sp("erreur"));
delete REP["/api/post/apercu"];
REP["/api/post/rendre"]={d:{detail:"la pile ne rend rien"},st:400};
sp("rendre").p.onClick();await calme();R.erreur_rendu=texte(sp("erreur"));
RETENIR=true;sp("instant").p.onChange({target:{value:"0.4"}});rendre();await tic();
sp("instant").p.onChange({target:{value:"0.8"}});rendre();await tic();R.attente_n=ATTENTE.length;
ATTENTE[2]();ATTENTE[3]();await calme();ATTENTE[0]();ATTENTE[1]();await calme();
R.retard=[sp("avant").p.src,sp("apres").p.src];RETENIR=false;
process.stdout.write(JSON.stringify(R));
})().catch(e=>{process.stdout.write(JSON.stringify({ERREUR:String(e&&e.stack||e)}))});
"""
with tempfile.NamedTemporaryFile("w", suffix=".cjs", delete=False, encoding="utf-8") as _f:
    _f.write(HARNAIS)
_rn = subprocess.run(["node", _f.name, str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
try:
    R = json.loads(_rn.stdout or "{}")
except ValueError:
    R = {"ERREUR": _rn.stdout[-400:] + _rn.stderr[-400:]}
os.unlink(_f.name)
print("[P] sous node")
check("P0 le harnais tourne", "ERREUR" not in R and R, (R.get("ERREUR") or _rn.stderr)[:600])
m = R.get("montage", {})
check("P1 au montage : catalogue, piles et sources chargés, attente avant le catalogue",
      "sonvfx.post.chargement" in R.get("attente", "")
      and set(m.get("appels", [])) >= {"/api/post/catalogue", "/api/post/presets", "/api/post/sources"}, m)
check("P2 familles avec leur compte, Rendus pressé ; un bouton par source ; « choisissez un rendu »",
      m.get("familles") == [["⟦sonvfx.post.f_rendus⟧ · 2", "true"], ["⟦sonvfx.post.f_vfx⟧ · 1", "false"],
                            ["⟦sonvfx.post.f_particules⟧ · 0", "false"]]
      and m.get("srcs") == 2 and "sonvfx.post.src_choisir" in m.get("attente", ""), m)
check("P3 catalogue : un bouton d'ajout par preset ; pile vide ; rendu impossible ; aucun aperçu sans source",
      m.get("ajouts") == [True] * 5 and m.get("pile_vide") is True and m.get("rendre_off") is True and m.get("apercus") == 0, m)
check("P4 famille vide : le dit ; VFX IA : ses seules sources", R.get("vide") is True and R.get("vfx") == "1:0",
      (R.get("vide"), R.get("vfx")))
c = R.get("calcul_avant_delai", {})
check("P5 choisir une source : pressée, « calcul » affiché, l'aperçu attend le délai", c == {"calc": True, "apercus": 0, "on": "true"}, c)
a = R.get("apercu1", {})
check("P6 après le délai : avant (pile vide) et après (la pile), source, t, largeur 960",
      a.get("corps") == [{"pile": [], "source": "jA", "t": 0, "largeur": 960}, {"pile": [], "source": "jA", "t": 0, "largeur": 960}]
      and a.get("avant", "").endswith(":avant") and a.get("apres", "").endswith(":avant") and a.get("calc") is False, a)
check("P7 curseur avant/après : l'image d'après rognée à gauche (50 % puis 30 %), proportions de la source, instant borné",
      a.get("clip") == "inset(0 0 0 50%)" and R.get("clip30") == "inset(0 0 0 30%)" and a.get("ratio") == "320/180"
      and a.get("instant") == [1.96, 0.04], (a, R.get("clip30")))
check("P8 changer l'instant relance l'aperçu à cet instant, les anciennes images libérées",
      R.get("instant") == [1.2, 1.2] and R.get("revoq", 0) >= 2, (R.get("instant"), R.get("revoq")))
a = R.get("ajout", {})
check("P9 ajouter : maillons dans l'ordre, le dernier déplié, intensité de l'effet (55) ou 100 % pour un mélange (LUT)",
      a.get("pile") == [["grain16", "false"], ["lut", "false"]] and a.get("deplie") == ["false", "true"]
      and a.get("inten") == [55, 100] and a.get("noms") == ["1. ⟦sonvfx.post.p_grain16⟧", "2. ⟦sonvfx.post.p_lut⟧"]
      and a.get("lut_reglages") == [True, True] and a.get("rendre_off") is False, a)
check("P10 l'aperçu envoie la pile : preset, intensité, masque, réglages au défaut du preset",
      (R.get("apercu_pile") or [None, None])[-1] == [{"preset": "grain16", "intensite": 55, "masque": False, "params": {}},
                                                      {"preset": "lut", "intensite": 100, "masque": False,
                                                       "params": {"preset": "teal_orange"}}],
      R.get("apercu_pile"))
check("P11 LUT : liste « ambiance intégrée » + LUT du serveur ; import .cube envoyé en multipart, choisi et listé",
      "sonvfx.post.lut_integree" in R.get("lut_options", "") and "Froid.cube" in R.get("lut_options", "")
      and (R.get("lut_import") or {}).get("appel") == ["/api/post/lut", "POST", [["fichier", "Chaud.cube"]]]
      and R["lut_import"]["file"] == "Chaud.cube" and "Chaud.cube" in R["lut_import"]["options"], R.get("lut_import"))
check("P12 intensité et réglages changés passent dans l'aperçu",
      (R.get("apercu_regle") or [None, None])[-1] == [{"preset": "grain16", "intensite": 80, "masque": False, "params": {}},
                                                      {"preset": "lut", "intensite": 100, "masque": False,
                                                       "params": {"preset": "cyberpunk", "file": "Chaud.cube"}}],
      R.get("apercu_regle"))
mk = R.get("masque", {})
check("P13 masquer : le maillon reste dans la pile, marqué, bouton pressé « Afficher » ; tout masqué = rendu impossible",
      mk.get("pile") == [["grain16", "true"], ["lut", "false"]] and mk.get("pressed") == "true"
      and mk.get("lbl") == "⟦sonvfx.post.afficher⟧" and R.get("tout_masque") is True, mk)
check("P14 dupliquer : la copie juste après l'original, mêmes réglages", (R.get("dup") or {}).get("pile")
      == [["grain16", "true"], ["grain16", "true"], ["lut", "false"]] and R["dup"]["inten"] == [80, 80, 100], R.get("dup"))
check("P15 monter / descendre ; le premier ne monte pas, le dernier ne descend pas",
      R.get("monter") == [["grain16", "true"], ["lut", "false"], ["grain16", "true"]] and R.get("bornes") == [True, True]
      and R.get("descendre") == [["lut", "false"], ["grain16", "true"], ["grain16", "true"]], (R.get("monter"), R.get("descendre")))
g = R.get("glisser", {})
check("P16 glisser-déposer : le maillon glissé prend la place de la cible",
      g.get("pile") == [["grain16", "true"], ["lut", "false"], ["grain16", "true"]]
      and g.get("pv") == 2 and g.get("d") == "2" and g.get("dr") is True, g)
check("P17 pile pleine (pile_max du serveur) : ajouts et duplication désactivés",
      R.get("plein") == {"n": 4, "off": [True] * 5, "dup": True}, R.get("plein"))
check("P18 supprimer un maillon", R.get("suppr") == [["grain16", "true"], ["lut", "false"], ["grain16", "true"]], R.get("suppr"))
e = R.get("enreg", {})
check("P19 enregistrer la pile : nom rogné, pile envoyée, ajoutée en tête et choisie, champ vidé",
      R.get("enreg_on") is True and (e.get("appel") or [None, None, {}])[0:2] == ["/api/post/presets", "POST"]
      and e["appel"][2]["nom"] == "Chaud" and [q["preset"] for q in e["appel"][2]["pile"]] == ["grain16", "lut", "grain16"]
      and e.get("sel") == "pz1" and e.get("nom") == "" and e.get("choix", "").index("Chaud") < e["choix"].index("Ancienne"), e)
check("P20 charger une pile : remplace la pile (preset inconnu écarté), réglages repris",
      (R.get("charge") or {}).get("pile") == [["vignette", "false"]] and R["charge"]["inten"] == [20], R.get("charge"))
check("P21 supprimer une pile enregistrée : le premier clic arme (aucun appel), le second supprime",
      (R.get("arme") or {}).get("appels") == 0 and R["arme"]["arme"] is True
      and R["arme"]["lbl"] == "⟦sonvfx.post.preset_confirmer⟧"
      and (R.get("suppr_preset") or {}).get("appel") == ["/api/post/presets/pa", "DELETE", None]
      and "Ancienne" not in R["suppr_preset"]["choix"], (R.get("arme"), R.get("suppr_preset")))
check("P22 vider la pile", R.get("videe") == [0, True, True], R.get("videe"))
rd = R.get("rendu", {})
check("P23 rendre : source, pile et titre rogné envoyés ; job annoncé ; bouton désactivé pendant le rendu",
      rd.get("appel") == ["/api/post/rendre", "POST", {"source": "jA", "pile": [{"preset": "vignette", "intensite": 60,
                                                                                 "masque": False, "params": {}}],
                                                       "titre": "Ma pile"}]
      and "sonvfx.post.rendu_cours" in rd.get("job", "") and rd.get("off") is True, rd)
check("P24 suivi du job chaque seconde : avancement affiché", (R.get("suivi") or {}).get("appel", [""])[0] == "/api/jobs/jpost1"
      and '"pct":40' in R["suivi"]["job"], R.get("suivi"))
f = R.get("fini", {})
check("P25 job fini : « rangé dans la Bibliothèque », sources relues, « Aller au Montage », plus de suivi",
      "sonvfx.post.rendu_ok" in f.get("job", "") and f.get("sources") is True and f.get("montage") is True
      and f.get("off") is False and R.get("aller") == ["montage"] and R.get("plus_de_suivi") == 0, (f, R.get("aller")))
check("P26 erreurs du serveur affichées (aperçu refusé, rendu refusé)",
      "preset de post-traitement inconnu" in R.get("erreur", "") and "la pile ne rend rien" in R.get("erreur_rendu", ""),
      (R.get("erreur"), R.get("erreur_rendu")))

check("P27 une réponse d'aperçu arrivée en retard (instant abandonné) est jetée : l'écran garde le dernier instant demandé",
      R.get("attente_n") == 4 and [str(u).split(":")[-1] for u in R.get("retard") or []] == ["t0.8avant", "t0.8apres"],
      (R.get("attente_n"), R.get("retard")))

print("[K] textes FR / EN")
DICO = json.loads((RACINE / "frontend" / "shared" / "i18n" / "sonvfx_hub.json").read_text(encoding="utf-8"))
CLES = sorted(set(re.findall(r'dzT\("(sonvfx\.post\.[a-z0-9_]+)"', PAGE)))
check("K1 chaque clé de la page : FR et EN, mêmes variables, trois segments",
      CLES and all((DICO.get(k) or {}).get("fr") and (DICO.get(k) or {}).get("en") and len(k.split(".")) == 3
                   and set(re.findall(r"\{(\w+)\}", DICO[k]["fr"])) == set(re.findall(r"\{(\w+)\}", DICO[k]["en"]))
                   for k in CLES), [k for k in CLES if k not in DICO])
check("K2 aucune clé sonvfx.post.* orpheline dans le dictionnaire",
      sorted(k for k in DICO if k.startswith("sonvfx.post.")) == CLES,
      sorted(set(k for k in DICO if k.startswith("sonvfx.post.")) ^ set(CLES)))
check("K3 un nom par preset du catalogue", all(f"sonvfx.post.p_{p}" in CLES for p in ORDRE))
_dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_bytes()
check("K4 dictionnaire assemblé (source = copie de dist)", CLES and all(k.encode() in _dico for k in CLES)
      and _dico == (RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js").read_bytes())

print(f"\n{ok} PASS / {fail} FAIL")
shutil.rmtree(_tmp, ignore_errors=True)


def test_sonvfx_post():
    assert fail == 0


if __name__ == "__main__":
    sys.exit(1 if fail else 0)
