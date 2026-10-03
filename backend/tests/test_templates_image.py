# -*- coding: utf-8 -*-
"""Plan-templates T5-T6 (tache #75 du suivi, PR A, 03/10/2026) — IMAGE FIXE d'un gabarit et VIGNETTES au contenu reel,
cote serveur.
DECISIONS DE L'UTILISATEUR (03/10) : echantillon choisi par case (metadata.samples), sinon mire neutre ; image DIRECTE
(graphe avant l'encodage video) ; instant reglable, 1 s par defaut ; sequentiel = l'acte qui joue ; export PNG/JPEG/WebP
vers la Bibliotheque (source « Templates ») avec recette ; vignettes a la demande, en cache, une a la fois.
Ce que le plan faisait faux, et que ce banc garde : toute case VIDE levait (export et vignettes en erreur sur presque
tout gabarit) ; la piste son restait construite sans etre branchee ; la cle de cache ignorait le kit de marque.
Preuve d'identite : SANS still_at, les commandes ffmpeg (spatiale et sequentielle) sont celles de la base a l'octet.
Temoin positif : la base (aa65a65f) n'a pas le module.
Run (depuis backend/) : & $PY tests/test_templates_image.py"""
import importlib.util, io, json, os, pathlib, shutil, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzimg_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs", "audio"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
          "FAL_KEY", "HEYGEN_API_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "aa65a65f"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_still.py"], capture_output=True, cwd=str(RACINE))
check("T1 temoin : la base n'a pas le module de l'image fixe", r0.returncode != 0)
from PIL import Image                                               # noqa: E402
try:
    from app.services import template_still as TS                   # noqa: E402
except ImportError as e:
    TS = None
    check("T2 le module existe", False, str(e))
from app.services import template_service as TSV                    # noqa: E402
from app.services.template_service import TemplateEngine            # noqa: E402
from app.config import settings                                     # noqa: E402
E = TemplateEngine()
FF = shutil.which("ffmpeg")
IMG = pathlib.Path(settings.images_path)


def reg(i, t, x, y, w, h, **kw):
    return dict({"id": i, "type": t, "x": x, "y": y, "width": w, "height": h, "z_index": 1}, **kw)


def tpl(regions, w=400, h=400, bg="#101010", **kw):
    return dict({"id": "tpl_i", "name": "i", "canvas": {"width": w, "height": h, "fps": 10, "duration_s": 2, "background_color": bg}, "regions": regions}, **kw)


def png_uni(nom, rgb, w=64, h=64):
    Image.new("RGB", (w, h), rgb).save(IMG / nom)
    return nom


def ouvrir(b):
    return Image.open(io.BytesIO(b)).convert("RGB")


print("[I] l'identite : sans still_at, rien ne change")
_sp = importlib.util.spec_from_file_location("ts_base", str(_tmp / "ts_base.py"))
(_tmp / "ts_base.py").write_bytes(subprocess.run(["git", "show", f"{BASE}:backend/app/services/template_service.py"], capture_output=True, cwd=str(RACINE)).stdout)
TSB = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(TSB)
png_uni("src.png", (200, 30, 30))
VID = _tmp / "v.mp4"
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=160x120:d=2:r=10", "-f", "lavfi", "-i", "sine=d=2",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(VID)], check=True)
SP = tpl([reg("v", "video_slot", 0, 0, 400, 200, slot_name="clip", audio_volume=1.0), reg("im", "image_slot", 0, 200, 200, 200, slot_name="pic"),
          reg("tx", "text_slot", 20, 300, 360, 60, slot_name="t", default_text="Titre", effect="pulse"), reg("tk", "ticker", 0, 360, 400, 40, text="defile")])
SV = {"clip": {"path": VID}, "pic": {"path": IMG / "src.png"}}
for d in ("wa", "wb"):
    (_tmp / d).mkdir(exist_ok=True)
ca = [str(x) for x in TSV.build_ffmpeg_command(E, SP, SV, _tmp / "o.mp4", _tmp / "wa")]
cb = [str(x).replace(str(_tmp / "wb"), str(_tmp / "wa")) for x in TSB.build_ffmpeg_command(E, SP, SV, _tmp / "o.mp4", _tmp / "wb")]
check("I1 commande SPATIALE (video avec son, image, texte pulse, ticker) identique a la base", ca == cb, next((f"{x} != {y}" for x, y in zip(ca, cb) if x != y), "longueurs"))
SQ = tpl([reg("a1", "video_slot", 0, 0, 400, 400, slot_name="a1", act=1, length_s=1), reg("a2", "image_slot", 0, 0, 400, 400, slot_name="a2", act=2,
          duration_s=1, transition={"type": "crossfade", "duration_s": 0.4})], render_mode="sequential")
qa = [str(x) for x in TSV.build_sequential_command(E, SQ, {"a1": {"path": VID}, "a2": {"path": IMG / "src.png"}}, _tmp / "q.mp4")[0]]
qb = [str(x) for x in TSB.build_sequential_command(E, SQ, {"a1": {"path": VID}, "a2": {"path": IMG / "src.png"}}, _tmp / "q.mp4")[0]]
check("I2 commande SEQUENTIELLE identique a la base", qa == qb, next((f"{x} != {y}" for x, y in zip(qa, qb) if x != y), "longueurs"))

print("\n[S] l'image fixe")
if TS and FF:
    D = _tmp / "outputs" / "_tmp_still"
    png_uni("rouge.png", (255, 0, 0)); png_uni("vert.png", (0, 255, 0))
    G = tpl([reg("v", "video_slot", 0, 0, 200, 200, slot_name="clip"), reg("im", "image_slot", 200, 0, 200, 200, slot_name="pic"),
             reg("tx", "text", 20, 300, 360, 80, text="BONJOUR", size=40, color="#ffffff")], metadata={"samples": {"pic": "rouge.png"}})
    a = ouvrir(TS.rendre(E, G, 1.0, "png", D))
    rouge = a.getpixel((300, 100))
    mire = [a.getpixel((x, y)) for x in range(5, 195, 7) for y in range(5, 195, 7)]
    check("S1 une image a la taille de la toile ; la case AVEC echantillon le montre (rouge), celle SANS montre une mire (pas le fond), le texte est la",
          a.size == (400, 400) and rouge[0] > 240 and rouge[1] < 15 and rouge[2] < 15 and len(set(mire)) > 2 and any(sum(p) > 300 for p in mire)
          and any(sum(a.getpixel((x, y))) > 600 for x in range(20, 380) for y in range(300, 380)), f"{a.size} {rouge} {len(set(mire))}")
    mp4 = E.render("v", {"clip": {"path": IMG / "rouge.png"}, "pic": {"path": IMG / "rouge.png"}}, _tmp / "outputs" / "cmp.mp4",
                   template=tpl([reg("im", "image_slot", 0, 0, 400, 400, slot_name="pic"), reg("v", "video_slot", 0, 0, 40, 40, slot_name="clip")]))
    subprocess.run([FF, "-y", "-v", "error", "-ss", "1", "-i", str(mp4), "-frames:v", "1", str(_tmp / "cmp.png")], check=True)
    vid = Image.open(_tmp / "cmp.png").convert("RGB").getpixel((300, 300))
    check("S2 l'image est prise AVANT l'encodage video : un rouge pur reste PUR (la video, elle, l'altere)",
          rouge == (255, 0, 0) and vid != (255, 0, 0), f"image={rouge} video={vid}")
    TK = tpl([reg("k", "ticker", 0, 150, 400, 80, text="DEFILE", speed=200, color="#ffffff")], bg="#000000")
    t0, t1 = ouvrir(TS.rendre(E, TK, 0, "png", D)), ouvrir(TS.rendre(E, TK, 1.0, "png", D))
    encre = lambda im: sum(1 for x in range(0, 400, 2) for y in range(150, 230, 2) if sum(im.getpixel((x, y))) > 400)
    tard = ouvrir(TS.rendre(E, TK, 999, "png", D))
    check("S3 l'INSTANT compte : a t = 0 le ticker n'est pas entre, a 1 s il l'est ; un instant au-dela de la duree donne la derniere image (pas d'erreur)",
          encre(t0) < encre(t1) and encre(t1) > 20 and tard.size == (400, 400), f"{encre(t0)} {encre(t1)}")
    shutil.copy(VID, _tmp / "audio" / "musique.mp4")
    AU = tpl([reg("v", "video_slot", 0, 0, 400, 400, slot_name="clip", audio_volume=1.0)], audio={"music": {"file": "musique.mp4"}, "fade_in_s": 1})
    try:
        au = ouvrir(TS.rendre(E, AU, 1.0, "png", D)); e_au = None
    except Exception as e:
        au, e_au = None, str(e)[-300:]
    check("S4 un gabarit AVEC son (case video sonore + musique) donne son image : la piste son n'est ni construite ni branchee", au is not None and au.size == (400, 400), str(e_au))
    jp, wb = TS.rendre(E, G, 1.0, "jpeg", D), TS.rendre(E, G, 1.0, "webp", D)
    check("S5 JPEG et WebP : les vrais formats (signatures), a la taille de la toile", jp[:3] == b"\xff\xd8\xff" and wb[:4] == b"RIFF" and wb[8:12] == b"WEBP"
          and ouvrir(jp).size == (400, 400) and ouvrir(wb).size == (400, 400))
    SQ2 = tpl([reg("a1", "video_slot", 0, 0, 400, 400, slot_name="a1", act=1), reg("a2", "image_slot", 0, 0, 400, 400, slot_name="a2", act=2, duration_s=2,
               transition={"type": "cut"})], render_mode="sequential", metadata={"samples": {"a1": "rouge.png", "a2": "vert.png"}})
    SQ2["canvas"]["fps"] = 30   # sous 25 i/s, la « coupe » (xfade 0,04 s) perd l'acte suivant — defaut existant, signale a part
    s1, s2, s3 = ouvrir(TS.rendre(E, SQ2, 1.0, "png", D)), ouvrir(TS.rendre(E, SQ2, 5.0, "png", D)), ouvrir(TS.rendre(E, SQ2, 999, "png", D))
    check("S6 sequentiel : l'acte qui JOUE a l'instant (acte 1 rouge a 1 s, acte 2 vert a 5 s) ; un acte video rempli d'une image dure 4 s",
          s1.getpixel((200, 200))[0] > 200 and s1.getpixel((200, 200))[1] < 60 and s2.getpixel((200, 200))[1] > 200 and s2.getpixel((200, 200))[0] < 60
          and s3.getpixel((200, 200))[1] > 200,
          f"{s1.getpixel((200, 200))} {s2.getpixel((200, 200))}")
    def refus(t, at=1.0, fmt="png"):
        try:
            TS.rendre(E, t, at, fmt, D); return None
        except ValueError as e:
            return str(e)
    rf = [refus(G, fmt="gif"), refus(G, at=-1), refus(G, at="midi"), refus(tpl([reg("im", "image_slot", 0, 0, 10, 10, slot_name="pic")], metadata={"samples": {"autre": "rouge.png"}})),
          refus(tpl([reg("im", "image_slot", 0, 0, 10, 10, slot_name="pic")], metadata={"samples": {"pic": "../secret.png"}})),
          refus(tpl([reg("im", "image_slot", 0, 0, 10, 10, slot_name="pic")], metadata={"samples": {"pic": "notes.txt"}}))]
    check("S7 refus parlants : format, instant negatif ou illisible, echantillon d'une case inconnue, chemin qui sort de la Bibliotheque, fichier non image",
          all(rf) and "webp" in rf[0] and "3600" in rf[1] and "secondes" in rf[2] and "autre" in rf[3] and "png, jpg, webp" in rf[4] and "png, jpg, webp" in rf[5], str(rf))
    absent = ouvrir(TS.rendre(E, tpl([reg("im", "image_slot", 0, 0, 400, 400, slot_name="pic")], metadata={"samples": {"pic": "efface.png"}}), 1.0, "png", D))
    check("S8 un echantillon EFFACE de la Bibliotheque retombe sur la mire (pas d'erreur)", absent.getpixel((200, 200))[0] < 100 and len({absent.getpixel((x, 50)) for x in range(0, 400, 9)}) > 1)
    FXT = tpl([reg("im", "image_slot", 0, 0, 400, 400, slot_name="pic", effects=[{"type": "vignette", "intensity": 50}])])
    (_tmp / "wfx").mkdir(exist_ok=True)
    cf = " ".join(map(str, TSV.build_ffmpeg_command(E, FXT, {"pic": {"path": IMG / "rouge.png"}}, _tmp / "x.png", _tmp / "wfx", still_at=1)))
    cs = " ".join(map(str, TSV.build_ffmpeg_command(E, G, {"clip": {"path": IMG / "vert.png"}, "pic": {"path": IMG / "rouge.png"}}, _tmp / "y.png", _tmp / "wfx", still_at=1)))
    FXP = dict(G, post_effects=[{"type": "vignette", "intensity": 50}])
    cp_ = " ".join(map(str, TSV.build_ffmpeg_command(E, FXP, {"clip": {"path": IMG / "vert.png"}, "pic": {"path": IMG / "rouge.png"}}, _tmp / "z.png", _tmp / "wfx", still_at=1)))
    check("S10 RGB seulement SANS effet : une case a effet ou un effet global garde la composition yuv de la video (fidele) ; sinon base, cases et superpositions en RGB",
          "gbrp" not in cf and "format=yuv420p[base]" in cf and "gbrp" not in cp_ and "format=gbrp[base]" in cs and cs.count(":format=gbrp[") >= 2
          and "format=gbrp[s" in cs, cf[-200:])
    mm = Image.open(TS.mire({"type": "video_slot", "width": 1080, "height": 1920, "slot_label": "Seedance animation (top, full width 1080)"},
                            _tmp / "mire.png")).convert("RGB")
    clair = [x for x in range(mm.width) for y in range(int(mm.height * 0.35), int(mm.height * 0.5), 4) if sum(mm.getpixel((x, y))) > 600]
    check("M1 la mire garde les PROPORTIONS de la case (1080x1920 -> 720x1280) et un long nom TIENT dans sa largeur (rien de rogne)",
          mm.size == (720, 1280) and clair and min(clair) > mm.width * 0.04 and max(clair) < mm.width * 0.96, f"{mm.size} {min(clair) if clair else None}-{max(clair) if clair else None}")
    check("S9 rien ne reste derriere (ni dossier de travail, ni mire)", not [p for p in D.rglob("*") if p.is_file()], str(list(D.rglob("*"))[:5]))
else:
    check("S0 le module et ffmpeg sont la", False)

print("\n[V] les vignettes")
if TS and FF:
    C = _tmp / "thumbs"
    B = E.get_template("tpl_news_reel")
    t0_ = time.time(); f1 = TS.vignette(E, B, C, D); d1 = time.time() - t0_
    t0_ = time.time(); f2 = TS.vignette(E, B, C, D); d2 = time.time() - t0_
    with Image.open(f1) as _im:
        im_size = _im.size
    check("V1 un gabarit LIVRE (cases video vides) donne sa vignette WebP, 360 px au plus grand cote ; la deuxieme fois vient du CACHE",
          f1.suffix == ".webp" and max(im_size) == 360 and f1 == f2 and d2 < d1 / 3, f"{im_size} {d1:.2f}/{d2:.2f}")
    B2 = json.loads(json.dumps(B)); B2.setdefault("metadata", {})["samples"] = {B2["regions"][0]["slot_name"]: "rouge.png"} if B2["regions"][0]["type"] in ("video_slot", "image_slot") else {}
    autre = TS.vignette(E, dict(B, id="tpl_news_reel_b"), C, D)
    f3 = TS.vignette(E, B2, C, D)
    check("V2 un echantillon change -> nouvelle vignette, l'ancienne du MEME gabarit part ; celle d'un gabarit au nom proche (tpl_news_reel_b) reste",
          f3 != f1 and f3.is_file() and not f1.exists() and autre.is_file(), str(sorted(p.name for p in C.iterdir())))
    from app.services import brand_kits as BK
    KT = json.loads(json.dumps(B)); KT["regions"].append(reg("kt", "text", 10, 10, 300, 60, text="{{brand.name}}"))
    k1 = TS.cle_vignette(E, KT)
    orig = BK.appliquer
    BK.appliquer = lambda t, kit=None: json.loads(json.dumps(t).replace("{{brand.name}}", "AUTRE MARQUE"))
    try:
        k2 = TS.cle_vignette(E, KT)
    finally:
        BK.appliquer = orig
    k3 = TS.cle_vignette(E, B2)
    time.sleep(1.1); png_uni("rouge.png", (250, 10, 10), 80, 80)
    check("V4 la cle suit aussi le FICHIER d'echantillon (meme nom, contenu remplace -> nouvelle vignette)", TS.cle_vignette(E, B2) != k3)
    check("V3 la cle suit le gabarit RESOLU : changer le kit de marque change la vignette", k1 != k2, f"{k1} {k2}")

print("\n[W] les routes et la Bibliotheque")
if TS and FF:
    from fastapi.testclient import TestClient                       # noqa: E402
    from app.main import app                                        # noqa: E402
    import app.main as _MAIN                                        # noqa: E402
    from app.services import library_index as LI                    # noqa: E402

    async def _boucle_coupee():
        return None
    _MAIN.schedule_loop = _boucle_coupee
    with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
        w1 = c.post("/api/layout-templates/tpl_news_reel/render-image", json={"format": "webp", "at_s": 1.5})
        d1 = w1.json() if w1.status_code == 200 else {}
        fic = IMG / d1.get("filename", "_")
        rec = json.loads((IMG / f"{d1.get('filename')}.recette.json").read_text(encoding="utf-8")) if fic.is_file() else {}
        lst = c.get("/api/images").json() if fic.is_file() else {}
        w2 = c.post("/api/layout-templates/_editeur/render-image", json={"template": G, "format": "jpeg"})
        w3 = [c.post("/api/layout-templates/inconnu/render-image", json={}).status_code, c.post("/api/layout-templates/tpl_news_reel/render-image", json={"format": "bmp"}),
              c.post("/api/layout-templates/x/render-image", json={"template": "rien"}).status_code]
        v1 = c.get("/api/layout-templates/tpl_news_reel/thumb")
        v2 = c.get("/api/layout-templates/inconnu/thumb").status_code
    with TestClient(app, client=("192.168.1.20", 50000), raise_server_exceptions=False) as c2:
        w4 = c2.post("/api/layout-templates/tpl_news_reel/render-image", json={}).status_code
    entree = next((e for e in lst.get("images") or [] if e.get("filename") == d1.get("filename")), None) if isinstance(lst, dict) else None
    check("W1 EXPORT : un vrai WebP « tpl_still_* » dans la Bibliotheque, source « Templates », recette a cote (gabarit, instant, format)",
          w1.status_code == 200 and fic.is_file() and fic.read_bytes()[8:12] == b"WEBP" and d1["filename"].startswith("tpl_still_") and d1["filename"].endswith(".webp")
          and rec.get("template_id") == "tpl_news_reel" and rec.get("at_s") == 1.5 and rec.get("format") == "webp"
          and LI.heuristique(d1["filename"]) == "templates" and LI.SOURCES.get("templates") == "Templates"
          and entree is not None and entree.get("source") == "templates" and entree.get("source_origin") != "heuristique", f"{w1.status_code} {w1.text[:200]} {rec} {entree}")
    check("W2 le gabarit de l'EDITEUR (non enregistre) s'exporte aussi ; refus : inconnu 404, format 400 parlant, gabarit illisible 400 ; hors machine refuse",
          w2.status_code == 200 and w2.json()["filename"].endswith(".jpg") and w3[0] == 404 and w3[1].status_code == 400 and "webp" in w3[1].json()["detail"]
          and w3[2] == 400 and w4 in (401, 403), f"{w2.status_code} {w3[0]} {w3[2]} {w4}")
    check("W3 VIGNETTE : WebP, revalidee a chaque fois (no-cache) ; 404 pour un gabarit inconnu",
          v1.status_code == 200 and v1.headers.get("content-type") == "image/webp" and v1.headers.get("cache-control") == "no-cache" and v1.content[8:12] == b"WEBP" and v2 == 404,
          f"{v1.status_code} {v1.headers.get('content-type')} {v2}")

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
