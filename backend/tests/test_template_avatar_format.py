# -*- coding: utf-8 -*-
"""LE TEMPLATE IMPOSE LE FORMAT DE LA GENERATION HEYGEN (27/09/2026).

Symptome (rendu 427b1a6d, News Reel — reel + avatar, lance depuis le Studio) :
dans la zone avatar, une bande sombre de ~410 px puis le haut du crane,
coupe par le bandeau de marque.
CAUSE MESUREE sur le clip HeyGen fa705454 (1080x1920) : le graphe demande du
9:16 ; HeyGen centre l'avatar (presque carre, ~1080x1140) et comble haut
(lignes 0-410) et bas (1550-1920) de la couleur de fond #02060d. La region
avatar du template fait 1080x680 en `cover_top` : elle garde les 680
premieres lignes — la bande vide et le haut du crane.
CORRECTIF : `pipeline._heygen_aspect_for_slot` — chaque slot HeyGen est
genere au format HeyGen (9:16, 1:1, 16:9) le plus proche de SA region ;
`render_template` l'impose avant la generation.

METHODE. [1] la regle pure ; [2] `render_template` REEL (base sqlite
temporaire, template integre tpl_news_reel, composition ffmpeg reelle) avec
un faux `run_heygen` qui IMITE le comportement mesure de HeyGen : un avatar
1080x1140 (fond noir, « tete » = rectangle clair lignes 40-760) centre en
`contain` dans le format DEMANDE, sur fond #02060d. On lit ensuite, dans la
region avatar du rendu (lignes 1080-1760), les lignes ou la tete apparait.
HYPOTHESE DATEE : le placement de HeyGen en 16:9 (contain, centre) n'est pas
mesure — il suppose le meme comportement que le 9:16 mesure ; seule une
generation payante le prouvera.
TEMOIN : le `pipeline.py` de 02697be (git show) garde le 9:16 du graphe et
coupe la tete (la mesure voit le defaut).
Aucun appel reseau (run_heygen remplace). Regle des assertions negatives :
chaque « absent » a son temoin positif. Faute n6 : details par `_d()`.
Run : & $PY tests/test_template_avatar_format.py   (depuis backend/)
"""
import asyncio, importlib.util, json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzavfmt_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from loguru import logger                                  # noqa: E402
logger.remove()
from app.services import pipeline as PL                    # noqa: E402
from app.models.schemas import GenerateHeyGenRequest, TemplateSlotValue   # noqa: E402
from app.services.storage import init_db, JobRecord, async_session_factory  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:400]
    except Exception as e:                                   # pragma: no cover
        return f"(detail illisible : {e})"


FF = shutil.which("ffmpeg")
print(f"ffmpeg : {FF}")
BASE = "02697be"
OLD = None
try:
    _src = subprocess.run(["git", "show", f"{BASE}:backend/app/services/pipeline.py"],
                          cwd=str(BACKEND.parent), capture_output=True).stdout
    if _src:
        _p = pathlib.Path(TMP) / f"pipeline_{BASE}.py"
        _p.write_bytes(_src)
        _spec = importlib.util.spec_from_file_location(f"app.services._pl_{BASE}", str(_p))
        OLD = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(OLD)
except Exception as e:
    print(f"  (temoin {BASE} indisponible : {e})")
    OLD = None

TPL = PL.TemplateEngine().get_template("tpl_news_reel")
AV = next((r for r in TPL.get("regions", []) if r.get("slot_name") == "avatar"), {})
RY0, RY1 = int(AV.get("y", 0)), int(AV.get("y", 0)) + int(AV.get("height", 0))

print("\n[0] preconditions")
check("0.1 ffmpeg present", bool(FF), _d(FF))
check(f"0.2 temoin {BASE} importe et porte Pipeline.render_template",
      OLD is not None and hasattr(getattr(OLD, "Pipeline", None), "render_template"), _d(OLD is not None))
check("0.3 tpl_news_reel : region avatar 1080x680 en y 1080, cover_top",
      (AV.get("width"), AV.get("height"), AV.get("y"), AV.get("fit")) == (1080, 680, 1080, "cover_top"), _d(AV))
if not FF or OLD is None:
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)

print("\n[1] regle pure : format HeyGen le plus proche de la region")
_asp = getattr(PL, "_heygen_aspect_for_slot", None)


def reg(w, h, name="avatar", typ="video_slot"):
    return {"regions": [{"type": "text", "slot_name": name, "width": 10, "height": 999},
                        {"type": typ, "slot_name": name, "width": w, "height": h}]}


_cas = [((1080, 680), "16:9"), ((1080, 1920), "9:16"), ((1080, 1080), "1:1"), ((1920, 1080), "16:9"),
        ((1080, 1350), "1:1"), ((540, 960), "9:16"), ((1080, 1300), "1:1"), ((1080, 1500), "9:16"),
        # entre les seuils LOG et LINEAIRE : rapport 1,36 (log -> 16:9, lineaire -> 1:1) et 0,76 (log -> 1:1,
        # lineaire -> 9:16). L'ecart en log est symetrique (2:1 et 1:2 sont a la meme distance du carre).
        ((1360, 1000), "16:9"), ((760, 1000), "1:1")]
check("1.1 dix geometries -> 16:9, 9:16, 1:1, 16:9, 1:1 (4:5), 9:16, 1:1, 9:16, 16:9 (1,36), 1:1 (0,76)",
      callable(_asp) and [_asp(reg(w, h), "avatar") for (w, h), _ in _cas] == [a for _, a in _cas],
      _d([_asp(reg(w, h), "avatar") if callable(_asp) else None for (w, h), _ in _cas]))
check("1.2 tpl_news_reel, slot avatar -> 16:9 ; slot reel (1080x1080) -> 1:1",
      callable(_asp) and _asp(TPL, "avatar") == "16:9" and _asp(TPL, "reel") == "1:1",
      _d(_asp(TPL, "avatar") if callable(_asp) else None))
check("1.3 slot absent, region image, dimensions nulles ou illisibles -> None (temoin : 1.2 rend un format)",
      callable(_asp) and _asp(TPL, "avatar") is not None
      and _asp(TPL, "nope") is None and _asp(reg(1080, 680, typ="image_slot"), "avatar") is None
      and _asp(reg(0, 680), "avatar") is None and _asp(reg("x", 680), "avatar") is None,
      "")

print("\n[2] render_template reel : faux HeyGen au format DEMANDE, tete mesuree dans la region")


def fake_heygen_video(aspect, out):
    W, H = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}[aspect]
    g = (f"color=c=black:s=1080x1140:d=2:r=30,drawbox=x=300:y=40:w=480:h=720:color=white:t=fill,"
         f"scale=w={W}:h={H}:force_original_aspect_ratio=decrease[c];"
         f"color=c=0x02060d:s={W}x{H}:d=2:r=30[b];[b][c]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]")
    subprocess.run([FF, "-y", "-v", "error", "-filter_complex", g, "-f", "lavfi", "-t", "2", "-i",
                    "sine=frequency=220:sample_rate=48000", "-map", "[v]", "-map", "0:a", "-shortest",
                    "-c:v", "libx264", "-qp", "0", "-c:a", "aac", str(out)], check=True)


REEL = pathlib.Path(TMP) / "reel.mp4"
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x404040:s=1080x1080:d=2:r=30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(REEL)], check=True)


async def render_with(mod, tag, seen):

    async def fake_run_heygen(self, request, *, composition_id=None, layer_index=None):
        asp = request.aspect_ratio.value
        seen["aspect"] = asp
        jid = f"hg-{tag}"
        out = pathlib.Path(TMP) / f"{jid}.mp4"
        fake_heygen_video(asp, out)
        async with async_session_factory() as s:
            s.add(JobRecord(id=jid, status="done", progress=100, image_filename="a", video_path=str(out),
                            final_video_path=str(out), provider="heygen", aspect_ratio=asp))
            await s.commit()
        return jid

    mod.Pipeline.run_heygen = fake_run_heygen
    pl = mod.Pipeline()
    sv = {"reel": TemplateSlotValue(source_kind="file", file_path=str(REEL)),
          "avatar": TemplateSlotValue(source_kind="heygen", heygen=GenerateHeyGenRequest(
              avatar_id="a", voice_id="v", script="s", aspect_ratio="9:16"))}
    job = await pl.render_template("tpl_news_reel", sv, job_id=f"tpl-{tag}")
    async with async_session_factory() as s:
        jr = await s.get(JobRecord, job)
        return seen, (jr.final_video_path or jr.video_path) if jr else None, (jr.status, jr.error) if jr else None


def head_rows(path):
    """Lignes (canevas 1080x1920) ou la colonne centrale est blanche (la tete) ; seuil 210 :
    le separateur cyan (y 1076-1083, luminance ~180) n'est pas une tete."""
    raw = subprocess.run([FF, "-v", "error", "-ss", "1", "-i", str(path), "-frames:v", "1",
                          "-vf", "crop=4:1920:538:0,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    rows = [y for y in range(1920) if len(raw) >= (y + 1) * 4 and raw[y * 4 + 1] > 210]
    return rows


async def main():
    await init_db()
    res = {}
    for mod, tag in ((PL, "nouveau"), (OLD, "temoin")):
        seen = {}
        try:
            res[tag] = await render_with(mod, tag, seen)
        except Exception as e:
            res[tag] = (seen, None, f"ERR {str(e)[:1500]}")
    return res


RES = asyncio.run(main())
sn, pn, stn = RES.get("nouveau", ({}, None, None))
so, po, sto = RES.get("temoin", ({}, None, None))
check("2.1 le graphe demande 9:16, la generation part en 16:9 (region 1080x680)",
      sn.get("aspect") == "16:9", _d(sn, stn))
check(f"2.2 temoin {BASE} : la generation part en 9:16 (le format du graphe)", so.get("aspect") == "9:16",
      _d(so, sto))
hn = head_rows(pn) if pn and pathlib.Path(pn).exists() else []
ho = head_rows(po) if po and pathlib.Path(po).exists() else []
inn = [y for y in hn if RY0 <= y < RY1]
ino = [y for y in ho if RY0 <= y < RY1]
check("2.3 rendu : la tete est ENTIERE dans la region avatar (debut > 1080, fin < 1760 - 40, >= 400 lignes)",
      bool(inn) and min(inn) > RY0 and max(inn) < RY1 - 40 and len(inn) >= 400 and len(inn) == len(hn),
      _d(stn, (min(inn), max(inn), len(inn), len(hn)) if inn else None))
check(f"2.4 temoin {BASE} : tete visible sur < 300 lignes et coupee par le bas de la region",
      bool(ino) and len(ino) < 300 and max(ino) >= RY1 - 2, _d(sto, (min(ino), max(ino), len(ino)) if ino else None))
check("2.5 ... la tete du temoin commence apres une bande vide de >= 300 lignes (le symptome)",
      bool(ino) and min(ino) - RY0 >= 300, _d((min(ino) - RY0) if ino else None))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
