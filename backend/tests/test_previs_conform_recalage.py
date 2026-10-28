# -*- coding: utf-8 -*-
"""t336 (A6 du lot Scenario, 29/10/2026) — durée minimale des modèles et recalage mesuré, pour « Previs → plan ».

  [C] plan_conform (PUR) : Seedance rend 4 s au moins, MiniMax 5 s ; un clip plus court est étiré (×k ≤ 2) ou
      complété au noir (au-delà), au choix ; cadence hors 24-60 i/s ou WebM : transcodé ; Veo (sans clip) : rien ;
  [F] conform FABRIQUÉ par ffmpeg (petits clips lavfi) : le nombre d'images EXACT, la cadence, le noir à la queue ;
  [M] la dérive MESURÉE par corrélation des bords : +2, -3, +1 (noir), 0 sur un plan fixe (non fiable) ;
  [R] le recalage : conform défait, dérive retirée, nombre d'images EXACT de la previs, à sa cadence ;
  [D] devis : le conform prévu (mode, auto, secondes envoyées), la durée FACTURÉE qui en découle, le choix « noir »,
      un choix inconnu refusé ; un clip de 1 s n'est plus refusé (il est conformé) ;
  [T] tir : le clip ENVOYÉ est le conformé (4 s, 96 images), le rendu recalé (60 images), la dérive rangée dans la
      recette et le job, relue par /previs/sources (« dernier_rendu ») ; zéro réseau.
ffmpeg RÉEL. AUCUN appel réseau : les coutures de previs_plan sont des espions. Run (depuis backend/) :
& $PY tests/test_previs_conform_recalage.py"""
import asyncio
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dzprevis336_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir()
pathlib.Path(_tmp, "outputs").mkdir()
os.environ["FAL_KEY"] = "test-key"
for _k in ("ELEVENLABS_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
           "OPENAI_API_KEY", "OLLAMA_URL", "OPENROUTER_API_KEY"):
    os.environ[_k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if not shutil.which("ffmpeg"):
    print("SKIP: ffmpeg introuvable")
    sys.exit(0)

from loguru import logger  # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:600]}")


import fal_client  # noqa: E402

RESEAU = {"n": 0, "noms": []}


def _garde(nom):
    async def _refus(*a, **k):
        RESEAU["n"] += 1
        RESEAU["noms"].append(nom)
        raise RuntimeError(f"GARDE RESEAU : {nom} appelé dans un banc")
    return _refus


for _nom in ("submit_async", "subscribe_async", "run_async", "upload_file_async", "upload_async",
             "upload_image_async"):
    setattr(fal_client, _nom, _garde(_nom))

from httpx import AsyncClient, ASGITransport  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402
import app.main as _MAIN  # noqa: E402
from app.services import video_refs as VR, previs_plan as PV  # noqa: E402
from app.services.storage import init_db  # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee

W = pathlib.Path(_tmp)
IMG = W / "images"
UP = W / "outputs" / "uploads"
UP.mkdir(parents=True, exist_ok=True)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_db())


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def previs(dest, secondes, fps=24, fixe=False):
    """Une previs « clay » : un carré blanc au mouvement NON périodique sur fond gris (fixe : sans mouvement)."""
    x, y = ("150", "290") if fixe else ("150+120*sin(t*2.7)", "290+200*cos(t*1.9)")
    ff("-filter_complex", f"color=c=0x404040:s=360x640:r={fps}:d={secondes}[bg];"
       f"color=c=white:s=60x60:r={fps}:d={secondes}[b];[bg][b]overlay=x='{x}':y='{y}':shortest=1,format=yuv420p",
       "-frames:v", str(int(round(secondes * fps))), str(dest))
    return dest


def rendu_simule(src, dest, *, retard=0, etirer=None, noir_jusqua=None, fps=24, images=96):
    """Ce qu'un modèle rendrait : le look changé (négatif, 720×1280), décalé de `retard` images de previs (> 0 en
    retard, < 0 en avance), puis à la durée du clip ENVOYÉ (étiré ×k, ou complété au noir)."""
    pas = []
    if retard > 0:
        pas.append(f"tpad=start={retard}:start_mode=clone")
    elif retard < 0:
        pas += [f"trim=start_frame={-retard}", "setpts=PTS-STARTPTS"]
    pas += ["negate", "scale=720:1280"]
    if etirer:
        pas += [f"setpts=PTS*{etirer}", f"fps={fps}"]
    if noir_jusqua:
        pas += [f"tpad=stop_mode=add:stop={noir_jusqua}:color=black"]
    pas.append(f"tpad=stop_mode=clone:stop={images}")
    n = int(noir_jusqua or (images if etirer else 0)) or None
    ff("-i", str(src), "-vf", ",".join(pas), *(["-frames:v", str(n)] if n else []), "-r", str(fps),
       "-pix_fmt", "yuv420p", str(dest))
    return dest


def luma(path, i):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"select=eq(n\\,{i}),scale=32:32,format=gray",
                        "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True)
    return sum(r.stdout) / max(1, len(r.stdout))


S = "seedance-2.5-v2v"

# ── [C] le plan du conform (PUR) ─────────────────────────────────────────────
print("[C] plan_conform")
c = PV.plan_conform({"fps": 24, "images": 60}, S)
check("C1 Seedance, 2,5 s à 24 i/s : étiré ×1,6 jusqu'à 4 s (96 images), choix automatique, deux choix offerts",
      c and c["mode"] == "etirer" and c["auto"] and c["facteur"] == 1.6 and c["images_envoyees"] == 96
      and c["secondes_envoyees"] == 4.0 and c["plancher_s"] == 4.0 and c["choix_possibles"] == ["etirer", "noir"]
      and c["images_previs"] == 60, c)
c = PV.plan_conform({"fps": 24, "images": 60}, S, "noir")
check("C2 choix « noir » : complété au noir jusqu'à 4 s, facteur 1, auto False",
      c and c["mode"] == "noir" and not c["auto"] and c["facteur"] == 1.0 and c["images_envoyees"] == 96, c)
c = PV.plan_conform({"fps": 24, "images": 24}, S)
check("C3 1 s (×4 > 2) : le choix automatique passe au NOIR", c and c["mode"] == "noir" and c["auto"], c)
check("C4 5 s, 24 i/s, MP4 : rien à faire (None)", PV.plan_conform({"fps": 24, "images": 120}, S, nom="a.mp4") is None)
c = PV.plan_conform({"fps": 24, "images": 120}, S, nom="a.webm")
check("C5 WebM de 5 s : transcodé (même durée, aucun choix)", c and c["mode"] == "transcoder" and c["transcode"]
      and c["images_envoyees"] == 120 and c["choix_possibles"] == [], c)
c = PV.plan_conform({"fps": 15, "images": 75}, S, nom="a.mp4")
check("C6 15 i/s : transcodé à 24 i/s", c and c["mode"] == "transcoder" and c["fps_envoye"] == 24.0
      and c["images_envoyees"] == 120, c)
c = PV.plan_conform({"fps": 30000 / 1001, "images": 75, "fps_r": "30000/1001"}, S)
check("C7 29,97 i/s, 75 images (2,5 s) : 4 s = ceil(4 × 29,97) = 120 images, la fraction de la previs gardée",
      c and c["images_envoyees"] == 120 and c["fps_previs"] == "30000/1001" and c["secondes_envoyees"] >= 4.0, c)
check("C8 planchers : Seedance 4 s (registre), MiniMax / Hailuo 5 s, Veo inconnu (0)",
      VR.plancher_s(S) == 4.0 and VR.plancher_s("minimax-hailuo-02") == 5.0 and VR.plancher_s("hailuo-2.3") == 5.0
      and VR.plancher_s("veo-3.1-ref") == 0.0)
check("C9 Veo références (pas de clip) : aucun conform", PV.plan_conform({"fps": 24, "images": 24}, "veo-3.1-ref") is None)
try:
    PV.plan_conform({"fps": 24, "images": 24}, S, "ralentir")
    _e = None
except ValueError as e:
    _e = str(e)
check("C10 choix inconnu : ValueError qui liste les choix", _e and "etirer" in _e and "noir" in _e, _e)

# ── [F] le conform fabriqué ──────────────────────────────────────────────────
print("\n[F] conform ffmpeg")
P25 = previs(UP / "previs_25.mp4", 2.5)
inf = PV.infos_clip(P25)
check("F0 la sonde compte les IMAGES de la piste (60) et garde la fraction de cadence", inf["images"] == 60
      and inf["fps_r"] == "24/1", inf)
dest, ic, notes = PV.conformer_clip(P25, inf, S, 4, executer=True, dossier=W / "conf")
check("F1 étiré : un MP4 de 96 images à 24 i/s (4 s), une note qui le dit", ic["images"] == 96
      and abs(ic["fps"] - 24) < 0.01 and dest.suffix == ".mp4" and dest != P25 and ic["conform"]["mode"] == "etirer"
      and "ralenti ×1.60" in notes[0], (ic, notes))
dn, icn, notes = PV.conformer_clip(P25, inf, S, 4, choix="noir", executer=True, dossier=W / "conf")
check("F2 noir : 96 images, les 60 premières = la previs, la queue NOIRE", icn["images"] == 96
      and luma(dn, 10) > 40 and luma(dn, 90) < 20 and "noir" in notes[0], (icn, luma(dn, 10), luma(dn, 90)))
dd, idd, notes = PV.conformer_clip(P25, inf, S, 4)
check("F3 au devis (executer False) : rien d'écrit, le chemin reste la previs, les infos sont celles de l'ENVOI",
      dd == P25 and idd["secondes"] == 4.0 and idd["images"] == 96 and idd["conform"]["mode"] == "etirer"
      and not any(p.name.startswith("previs_25_conf") for p in UP.iterdir()), idd)
P5 = previs(UP / "previs_5.mp4", 5)
d5, i5, n5 = PV.conformer_clip(P5, PV.infos_clip(P5), S, 4, executer=True)
check("F4 un clip de 5 s : l'identité (rien fabriqué, aucune note)", d5 == P5 and n5 == [] and "conform" not in i5)
P15 = previs(UP / "previs_15.mp4", 5, fps=15)
d15, i15, _ = PV.conformer_clip(P15, PV.infos_clip(P15), S, 4, executer=True, dossier=W / "conf")
check("F5 15 i/s : transcodé à 24 i/s, 120 images", abs((i15["fps"] or 0) - 24) < 0.01 and i15["images"] == 120, i15)

# ── [M] la dérive mesurée ────────────────────────────────────────────────────
print("\n[M] dérive mesurée (corrélation des bords)")
cet = PV.plan_conform(inf, S)
cnoir = PV.plan_conform(inf, S, "noir")
cas = [("M1 étiré, rendu en RETARD de 2 images", dict(retard=2, etirer=1.6), cet, 2),
       ("M2 étiré, rendu en AVANCE de 3 images", dict(retard=-3, etirer=1.6), cet, -3),
       ("M3 noir, rendu en retard d'1 image", dict(retard=1, noir_jusqua=96), cnoir, 1),
       ("M4 noir, rendu calé", dict(retard=0, noir_jusqua=96), cnoir, 0)]
RENDUS = {}
for label, kw, conf, attendu in cas:
    r = rendu_simule(P25, W / f"r_{attendu}_{conf['mode']}.mp4", **kw)
    RENDUS[label] = (r, conf)
    m = PV.mesurer_derive(PV._vignettes(P25, "", "24/1"), PV._vignettes(r, PV._inverse(conf), "24/1"))
    check(f"{label} : mesuré {attendu:+d}, fiable", m["derive_images"] == attendu and m["fiable"], m)
FIXE = previs(UP / "fixe.mp4", 2.5, fixe=True)
rf = rendu_simule(FIXE, W / "r_fixe.mp4", retard=2, etirer=1.6)
m = PV.mesurer_derive(PV._vignettes(FIXE, "", "24/1"), PV._vignettes(rf, PV._inverse(cet), "24/1"))
check("M5 plan FIXE : rien à mesurer — dérive 0, non fiable (jamais une dérive inventée)",
      m["derive_images"] == 0 and m["fiable"] is False, m)
check("M6 la phrase affichée", PV.phrase_derive(2) == "dérive : +2 images, recalée"
      and PV.phrase_derive(-1) == "dérive : -1 image, recalée" and "non mesurable" in PV.phrase_derive(0, False))

# ── [R] le recalage ──────────────────────────────────────────────────────────
print("\n[R] recalage")
for label, attendu in (("M1 étiré, rendu en RETARD de 2 images", 2), ("M2 étiré, rendu en AVANCE de 3 images", -3),
                       ("M3 noir, rendu en retard d'1 image", 1)):
    r, conf = RENDUS[label]
    rc = PV.recaler(r, P25, inf, conf, dossier=W / "rc")
    iv = PV.infos_clip(rc["video"])
    apres = PV.mesurer_derive(PV._vignettes(P25, "", "24/1"), PV._vignettes(rc["video"], "", "24/1"))
    check(f"R{attendu:+d} {label.split(' ', 1)[1]} : 60 images EXACTES à 24 i/s, dérive {attendu:+d} retirée "
          f"(re-mesurée 0)", rc["derive_images"] == attendu and iv["images"] == 60 and iv["fps_r"] == "24/1"
          and apres["derive_images"] == 0 and rc["phrase"] == PV.phrase_derive(attendu), (rc, iv, apres))
r_noir = RENDUS["M3 noir, rendu en retard d'1 image"][0]
rc = PV.recaler(r_noir, P25, inf, cnoir, dossier=W / "rc2")
check("R4 noir : la queue noire est COUPÉE (dernière image recalée non noire)", luma(rc["video"], 59) > 40,
      luma(rc["video"], 59))
P2997 = W / "p2997.mp4"
ff("-i", str(previs(W / "p30.mp4", 2.5, fps=30)), "-vf", "setpts=PTS*1.001", "-r", "30000/1001", "-pix_fmt",
   "yuv420p", str(P2997))
i2997 = PV.infos_clip(P2997)
c2997 = PV.plan_conform(i2997, S)
r2997 = rendu_simule(P2997, W / "r2997.mp4", retard=2, etirer=c2997["facteur"], fps="30000/1001",
                     images=c2997["images_envoyees"])
rc = PV.recaler(r2997, P2997, i2997, c2997, dossier=W / "rc3")
iv = PV.infos_clip(rc["video"])
check("R5 29,97 i/s : la fraction exacte gardée, le nombre d'images de la previs, la dérive +2",
      iv["fps_r"] == "30000/1001" and iv["images"] == i2997["images"] and rc["derive_images"] == 2, (i2997, iv, rc))

# ── le décor de la route ─────────────────────────────────────────────────────
TELEVERSES, SOUMIS = [], []
RENDU_FAL = {"src": None}


async def _upload(path):
    p = pathlib.Path(path)
    TELEVERSES.append((p.name, PV.infos_clip(p) if p.suffix == ".mp4" else None))
    return f"https://fal.test/up/{p.name}"


async def _fal_subscribe(endpoint, arguments):
    SOUMIS.append((endpoint, json.loads(json.dumps(arguments))))
    return {"video": {"url": "https://fal.test/out/rendu.mp4"}, "seed": 7}


async def _download(url, dest):
    shutil.copy(RENDU_FAL["src"], dest)

PV._upload, PV._fal_subscribe, PV._download = _upload, _fal_subscribe, _download


def sql(q, *a):
    con = sqlite3.connect(str(W / "t.db"))
    try:
        r = con.execute(q, a)
        con.commit()
        return r.fetchall()
    finally:
        con.close()


async def _req(meth, path, body=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testclient", timeout=300) as cl:
        if meth == "GET":
            return await cl.get("/api" + path)
        return await cl.post("/api" + path, json=body)


def call(meth, path, body=None):
    return loop.run_until_complete(_req(meth, path, body))


def js(r):
    try:
        return r.json()
    except Exception:  # noqa: BLE001
        return {}


ch = js(call("POST", "/chapters", {"title": "C", "script_text": "Vane entre.\n\nLa table tombe."}))
shots = js(call("POST", f"/chapters/{ch.get('id')}/storyboard/decoupe", {"method": "paragraph"})).get("shots", [])
s0 = shots[0]["id"]
Image.new("RGB", (90, 160), (200, 40, 40)).save(IMG / "prod0.png")
sql("UPDATE shots SET image=?, duration_s=2.5 WHERE id=?", "prod0.png", s0)
fini = W / "outputs" / "final" / "previs_job.mp4"
fini.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(P25, fini)
sql("INSERT INTO jobs (id, status, progress, title, image_filename, final_video_path, duration_s, created_at) "
    "VALUES (?,?,?,?,?,?,?,?)", "job-previs", "done", 100, "previs clay", "prod0.png", str(fini), 2,
    "2026-10-28 10:00:00")
shutil.copy(previs(W / "un.mp4", 1.0), UP / "une_seconde.mp4")

print("\n[D] devis")
r = call("POST", f"/shots/{s0}/previs/devis", {"clip_id": "job-previs"})
d = js(r)
cf = d.get("conform") or {}
check("D1 clip de 2,5 s : conform PRÉVU « etirer » automatique ×1,6, 4 s envoyées ; le clip reste décrit à 2,5 s",
      r.status_code == 200 and d.get("refus") is None and cf.get("mode") == "etirer" and cf.get("auto") is True
      and cf.get("secondes_envoyees") == 4.0 and abs((d.get("clip") or {}).get("secondes", 0) - 2.5) < 0.05
      and (d.get("clip") or {}).get("images") == 60, r.text[:500])
check("D2 la durée FACTURÉE suit le conform : 4 s d'entrée + 4 s de sortie, (4 + 4) × 0,473 × 0,6",
      d.get("secondes_entree") == 4.0 and d.get("secondes_sortie") == 4.0
      and d.get("usd") == VR.cout_estime(S, 4, entree_s=4, resolution="720p"), d)
r = call("POST", f"/shots/{s0}/previs/devis", {"clip_id": "job-previs", "conform": "noir"})
check("D3 choix « noir » : conform noir, auto False, même durée facturée", r.status_code == 200
      and (js(r).get("conform") or {}).get("mode") == "noir" and (js(r).get("conform") or {}).get("auto") is False
      and js(r).get("secondes_entree") == 4.0, r.text[:300])
r = call("POST", f"/shots/{s0}/previs/devis", {"clip_id": "job-previs", "conform": "ralentir"})
check("D4 choix inconnu : refus DIT", r.status_code == 200 and "ralentir" in (js(r).get("refus") or ""), r.text[:300])
r = call("POST", f"/shots/{s0}/previs/devis", {"video_filename": "une_seconde.mp4"})
check("D5 un clip de 1 s n'est plus refusé : complété au NOIR (×4 > 2), 4 s facturées", r.status_code == 200
      and js(r).get("refus") is None and (js(r).get("conform") or {}).get("mode") == "noir"
      and js(r).get("secondes_entree") == 4.0, r.text[:300])
r = call("POST", f"/shots/{s0}/previs", {"clip_id": "job-previs", "conform": "ralentir", "confirme_cout": True})
check("D6 tir avec un choix inconnu : 400, rien envoyé", r.status_code == 400 and not SOUMIS, r.text[:300])

print("\n[T] tir : conform envoyé, rendu recalé")
RENDU_FAL["src"] = RENDUS["M1 étiré, rendu en RETARD de 2 images"][0]
avant = set(p.name for p in UP.iterdir())
r = call("POST", f"/shots/{s0}/previs", {"clip_id": "job-previs", "confirme_cout": True})
jid = js(r).get("job_id")
check("T1 le tir : 200, usd = le devis", r.status_code == 200 and jid and js(r).get("usd") == d.get("usd"),
      r.text[:300])
env = TELEVERSES[0] if TELEVERSES else (None, None)
check("T2 le clip ENVOYÉ est le conformé : 96 images (4 s) à 24 i/s, pas la previs de 2,5 s",
      env[0] and "_conf_" in env[0] and env[1] and env[1]["images"] == 96, TELEVERSES)
check("T3 Seedance reçoit le conformé (editing, sans durée : il suit le clip de 4 s)",
      SOUMIS and SOUMIS[0][1].get("video_urls") == [f"https://fal.test/up/{env[0]}"]
      and SOUMIS[0][1].get("task") == "editing", SOUMIS)
job = sql("SELECT status, final_video_path, cost_meta, error FROM jobs WHERE id=?", jid)
fv = pathlib.Path(job[0][1]) if job and job[0][1] else None
check("T4 le rendu recalé : 60 images EXACTES (la previs), 24 i/s, sous le nom du rendu (previs_*.mp4)",
      job and job[0][0] == "done" and fv and fv.is_file() and fv.name.startswith("previs_")
      and "_recale" not in fv.name and PV.infos_clip(fv)["images"] == 60, job)
meta = json.loads(job[0][2]) if job and job[0][2] else {}
check("T5 le job garde le conform et le recalage : dérive +2, fiable, 60 images, la phrase",
      (meta.get("conform") or {}).get("mode") == "etirer" and (meta.get("recalage") or {}).get("derive_images") == 2
      and meta["recalage"]["fiable"] is True and meta["recalage"]["images"] == 60
      and meta["recalage"]["phrase"] == "dérive : +2 images, recalée", meta)
lib = sql("SELECT recette FROM library_assets WHERE job_id=?", jid)
rec = json.loads(lib[0][0]) if lib and lib[0][0] else {}
check("T6 la recette (Bibliothèque) : conform et recalage, la note du conform parmi les notes",
      (rec.get("recalage") or {}).get("derive_images") == 2 and (rec.get("conform") or {}).get("facteur") == 1.6
      and any("ralenti" in n for n in rec.get("notes", [])), rec)
apres = set(p.name for p in UP.iterdir()) - avant
check("T7 le clip conformé est effacé après l'envoi ; aucun « _recale » ne traîne", not any("_conf_" in n or "_recale" in n
                                                                                       for n in apres), apres)
src = js(call("GET", f"/shots/{s0}/previs/sources")).get("dernier_rendu") or {}
check("T8 /previs/sources relit le dernier rendu du plan et sa dérive", src.get("job_id") == jid
      and (src.get("recalage") or {}).get("derive_images") == 2, src)
check("T9 aucun appel réseau dans tout le banc", RESEAU["n"] == 0, RESEAU)
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
