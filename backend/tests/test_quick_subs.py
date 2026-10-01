# -*- coding: utf-8 -*-
"""Plan Quick T4 (tache #50 du suivi, 01/10/2026) — sous-titres GRAVES sur le rendu Quick.

La gravure est mesuree sur le PIXEL : une image extraite du mp4 grave est plus claire, dans la bande basse, que la meme
image du mp4 d'origine ; l'.ass ecrit est relu. Le chemin gratuit (calage du texte connu) est le defaut ; la
transcription PAYANTE n'est jamais appelee sans demande explicite (espion), et les trois routes Quick la chiffrent
dans leur garde des plafonds QUAND elle est demandee (devis compare avec / sans). Aucun reseau. Data-dir isole.
Run (depuis backend/) : & $PY tests/test_quick_subs.py"""
import asyncio, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzqsubs_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["HEYGEN_API_KEY"] = "test-heygen"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from loguru import logger                                           # noqa: E402
logger.remove()
from PIL import Image                                               # noqa: E402
from app.services import quick_finish as QF, transcribe_service as T  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


TEXTE = "Des profondeurs, le prophete parle. Le banc se reveille et la lumiere descend."
transcrits = []
T.transcribe = lambda *a, **k: (transcrits.append(a), (_ for _ in ()).throw(RuntimeError("espion : aucun reseau")))[1]


def _exe(n):
    return shutil.which(n) or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin" + f"\\{n}.exe")


def _clip(nom):
    p = _tmp / nom
    subprocess.run([_exe("ffmpeg"), "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=#02060d:s=540x960:r=24:d=6",
                    "-f", "lavfi", "-i", "sine=frequency=220:duration=6", "-pix_fmt", "yuv420p", "-shortest", str(p)],
                   check=True, timeout=180)
    return p


def _bande_basse(video, t):
    png = _tmp / f"{video.stem}_{t}.png"
    subprocess.run([_exe("ffmpeg"), "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", str(png)],
                   check=True, timeout=120)
    im = Image.open(png).convert("L")
    w, h = im.size
    px = list(im.crop((0, int(h * 0.72), w, h)).getdata())
    return sum(px) / float(len(px))


print("\n[A] gravure mesuree au pixel (chemin gratuit)")
src = _clip("nu.mp4")
grave = _tmp / "grave.mp4"
shutil.copy2(src, grave)
segs = QF.segments_for(grave, TEXTE, lang="fr", source="align", cps=42)
check("A1 au moins deux repliques, dans la duree du clip", len(segs) >= 2 and segs[0]["start"] < segs[-1]["end"] <= 6.2, str(segs)[:200])
ass = QF.burn(grave, segs, style="pop", ratio="9:16")
avant, apres = _bande_basse(src, 1.0), _bande_basse(grave, 1.0)
check("A2 du texte clair est apparu dans la bande basse", apres > avant + 3.0, f"{avant:.1f} -> {apres:.1f}")
t = ass.read_text("utf-8")
check("A3 l'.ass est en 1080x1920 et porte le texte", "PlayResY: 1920" in t and "prophete" in t.lower(), t[:200])
check("A4 aucun appel de transcription", transcrits == [])
try:
    QF.segments_for(src, "   ", lang="fr", source="align"); m = ""
except ValueError as e:
    m = str(e).lower()
check("A5 sans texte, le chemin gratuit refuse en le disant (et nomme la transcription payante)", "aucun texte" in m and "transcription" in m, m)
try:
    QF.segments_for(src, TEXTE, source="pirate"); m = ""
except ValueError as e:
    m = str(e)
check("A6 une source inconnue est refusee", "source inconnue" in m, m)
taille = grave.stat().st_size
try:
    QF.burn(grave, [], style="pop"); m = ""
except ValueError as e:
    m = str(e)
check("A7 rien a graver : refus, le mp4 n'est pas touche", "aucune réplique" in m and grave.stat().st_size == taille, m)

print("\n[B] le crochet du pipeline ne leve jamais et ne paie pas sans demande")
r = asyncio.run(QF.apply(_tmp / "absent.mp4", {"on": True}, text=TEXTE, ratio="9:16"))
check("B1 fichier absent : compte rendu d'erreur, pas d'exception", r.get("on") is True and r.get("error"), str(r))
v2 = _clip("v2.mp4")
r = asyncio.run(QF.apply(v2, {"on": True, "source": "align"}, text="", ratio="9:16"))
check("B2 sans texte et sans demande : AUCUNE transcription, l'erreur le dit", transcrits == [] and "aucun texte" in r.get("error", "").lower(), str(r))
r = asyncio.run(QF.apply(v2, {"on": True}, text="", ratio="9:16"))
check("B3 source absente = align (jamais transcribe par defaut)", transcrits == [] and "aucun texte" in r.get("error", "").lower(), str(r))
r = asyncio.run(QF.apply(v2, {"on": True, "source": "transcribe"}, text="", ratio="9:16"))
check("B4 temoin : demandee explicitement, la transcription est appelee (espion)", len(transcrits) == 1 and r.get("error"), str(r))
check("B5 off : rien", asyncio.run(QF.apply(v2, {"on": False}, text=TEXTE, ratio="9:16")) == {"on": False} and asyncio.run(QF.apply(v2, None, text=TEXTE, ratio="9:16")) == {"on": False})
check("B6 transcription_demandee : seulement on + source transcribe", QF.transcription_demandee({"on": True, "source": "transcribe"})
      and not QF.transcription_demandee({"on": False, "source": "transcribe"}) and not QF.transcription_demandee({"on": True})
      and not QF.transcription_demandee(None))

print("\n[C] les routes chiffrent la transcription SEULEMENT quand elle est demandee")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import plafonds as P                              # noqa: E402
(settings.images_path / "a.png").write_bytes(b"\x89PNG\r\n\x1a\nstub")
SUBS_T = {"on": True, "source": "transcribe", "provider": "elevenlabs", "lang": "fr"}
SUBS_A = {"on": True, "source": "align", "text": TEXTE}


def devis(c, url, corps):
    r = c.post(url, json=corps)
    d = r.json().get("detail") if r.headers.get("content-type", "").startswith("application/json") else None
    return r.status_code, ((d or {}).get("dz_plafond") or {}).get("devis_usd", 0) if isinstance(d, dict) else 0


with TestClient(app, client=("127.0.0.1", 50000)) as c:
    P.enregistrer({"global_usd": 0.000001, "par_moteur": {}, "alerte_pct": 80})
    seed = {"image_filename": "a.png", "custom_prompt": "abysse", "duration_s": 10}
    hg = {"avatar_id": "av1", "voice_id": "v1", "script": "salut " * 40}
    comp = {"seedance": dict(seed), "heygen": dict(hg)}
    for nom, url, corps in (("/generate", "/api/generate", seed), ("/generate/heygen", "/api/generate/heygen", hg),
                            ("/generate/composition", "/api/generate/composition", comp)):
        s0, d0 = devis(c, url, corps)
        sa, da = devis(c, url, dict(corps, subtitles=SUBS_A))
        st, dt = devis(c, url, dict(corps, subtitles=SUBS_T))
        check(f"C {nom} : le calage gratuit ne change pas le devis, la transcription demandee l'augmente",
              s0 == sa == st == 402 and d0 > 0 and abs(da - d0) < 1e-9 and dt > d0, f"{s0} {sa} {st} {d0} {da} {dt}")
    P.enregistrer({"global_usd": 0, "par_moteur": {}})
check("C4 aucun appel de transcription pendant les devis", len(transcrits) == 1)

print("\n[D] les crochets du pipeline (lecture STRUCTURELLE : un rendu complet demanderait les fournisseurs)")
import ast                                                          # noqa: E402
_src = (pathlib.Path(__file__).resolve().parents[1] / "app" / "services" / "pipeline.py").read_text("utf-8")
_fn = {n.name: ast.get_source_segment(_src, n) for n in ast.walk(ast.parse(_src)) if isinstance(n, ast.AsyncFunctionDef)}
r_run, r_hg, r_comp = _fn.get("run", ""), _fn.get("run_heygen", ""), _fn.get("run_composition", "")
check("D1 run : grave final_dest APRES le mix, texte = ecran sinon voix off REELLEMENT dite",
      "quick_finish.apply(final_dest, _subs" in r_run and r_run.find("quick_finish.apply(final_dest") > r_run.find("final_video_path=str(final_dest)") > 0
      and 'if request.voiceover_enabled else ""' in r_run)
check("D2 run_heygen : grave final_path apres sa mise a jour, texte = ecran sinon script de l'avatar",
      "quick_finish.apply(final_path, _subs" in r_hg and r_hg.find("quick_finish.apply(final_path") > r_hg.find("final_video_path=str(final_path)") > 0
      and '(request.script or "").strip()' in r_hg)
check("D3 run_composition : grave out_path apres la composition, avant le job parent, texte = script de l'avatar",
      "quick_finish.apply(out_path, _subs" in r_comp and r_comp.find("Unknown composition layout") < r_comp.find("quick_finish.apply(out_path")
      < r_comp.find('Create a "composition" parent job') and "request.heygen.script" in r_comp)

print(f"\n{ok} ok, {fail} echec(s)")
raise SystemExit(1 if fail else 0)
