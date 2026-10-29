# -*- coding: utf-8 -*-
"""t283 (23/10/2026) — la recette de génération suit le rendu : Bibliothèque → Quick / Studio.

[A] GET /api/jobs/{id}/recette : une recette unifiée. Ordre de lecture : recette Quick (le formulaire exact), puis
    colonnes du job (prompt EXACT envoyé, négatif, modèle, durée, format, graine, image de départ et de fin, style,
    espace, parent), puis recette d'import (jointe à l'upload, ou fichier <nom>.recette.json posé à côté de la vidéo).
    Aucun coût n'est repris (l'écran le réestime).
[B] POST /api/videos/upload : champ facultatif `recette` (objet JSON, 64 Ko au plus, sinon 400).
[C] Fiche audio : sans recette de génération, le prompt et le modèle gardés par Son & VFX (_sfx_meta.json).
[D] Écran : maillon de queue dzrecette (Envoyer vers, panneau de la fiche, Quick et Studio), aller-retour exact,
    comptes figés, textes FR/EN.
Run : & $PY tests/test_recette_rendu.py   (depuis backend/)
"""
import asyncio, io, json, os, sys, tempfile, pathlib
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzt283_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ.pop(k, None)
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
sys.path.insert(0, str(REPO / "scripts"))

ok = fail = 0
def J(r):
    """Le corps JSON d'une réponse, ou {} : une route absente rend la page de la SPA (HTML) et doit ROUGIR, pas planter."""
    try:
        v = r.json()
    except ValueError:
        return {}
    return v if isinstance(v, dict) else {}

def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")

from fastapi.testclient import TestClient                   # noqa: E402
from app.main import app                                    # noqa: E402
from app.config import settings                             # noqa: E402
from app.services import quick_recipe, sfx_service          # noqa: E402
from app.services.storage import JobRecord, async_session_factory  # noqa: E402

PROMPT = ("The giant bioluminescent jellyfish pulses and glides upward, its tentacles trail glowing particles, city "
          "lights flicker below, slow epic camera rise, cinematic")
NEG = "no morphing, no warping, no identity drift"


async def semer():
    async with async_session_factory() as s:
        s.add(JobRecord(id="job-api", status="done", progress=100, image_filename="gen_9b726482.png",
                        image_filename_end="fin.png", final_prompt=PROMPT, negative_prompt=NEG, seed=482831877,
                        duration_s=5, aspect_ratio="9:16", style="hybrid", template_id=None, provider="seedance",
                        video_model="seedance-2.5", espace_id="esp-1", parent_job_id="job-pere",
                        cost_meta='{"usd": 0.61}', final_video_path=str(pathlib.Path(TMP) / "a.mp4")))
        s.add(JobRecord(id="job-quick", status="done", progress=100, image_filename="dep.png",
                        final_prompt="prompt construit, tags", negative_prompt=NEG, seed=12, duration_s=10,
                        aspect_ratio="1:1", style="cinematic", provider="seedance", video_model="kling-3"))
        s.add(JobRecord(id="job-tpl", status="done", progress=100, image_filename="x.png", final_prompt="Subject: x.",
                        negative_prompt=NEG, seed=1, duration_s=8, aspect_ratio="9:16", style="cinematic",
                        template_id="tpl-3", provider="template"))
        await s.commit()


print("\n[A] GET /api/jobs/{id}/recette")
with TestClient(app) as c:
    asyncio.run(semer())
    quick_recipe.save("job-quick", {"v": 1, "tab": "seedance", "seedance": {"prompt": "le prompt SAISI", "vibe": "glitch",
                                                                              "model": "kling-3", "duration": 10,
                                                                              "aspect": "1:1", "seed": "12",
                                                                              "image": "dep.png", "end": ""}})
    (settings.outputs_path / "_graphs").mkdir(parents=True, exist_ok=True)
    (settings.outputs_path / "_graphs" / "job-tpl.json").write_text('{"nodes":[],"edges":[]}', encoding="utf-8")

    r = c.get("/api/jobs/job-api/recette"); j = J(r) if r.status_code == 200 else {}
    check("A1 rendu de l'API : 200", r.status_code == 200, r.text[:200])
    check("A2 source « job » (ni recette Quick ni graphe)", j.get("source") == "job" and j.get("quick") is None
          and j.get("studio") is False, str(j.get("source")))
    check("A3 le prompt EXACT envoyé (final_prompt, sans rien ajouter)", j.get("prompt") == PROMPT, repr(j.get("prompt")))
    check("A4 négatif, modèle, durée, format, graine, style", j.get("negative") == NEG and j.get("model") == "seedance-2.5"
          and j.get("duration_s") == 5 and j.get("aspect_ratio") == "9:16" and j.get("seed") == 482831877
          and j.get("style") == "hybrid", json.dumps(j)[:300])
    check("A5 images de départ et de fin", j.get("image") == "gen_9b726482.png" and j.get("image_end") == "fin.png")
    check("A6 espace, parent, provider", j.get("espace_id") == "esp-1" and j.get("parent_job_id") == "job-pere"
          and j.get("provider") == "seedance")
    check("A7 AUCUN coût repris (l'écran réestime)", "usd" not in json.dumps(j) and "cost" not in json.dumps(j)
          and "cout" not in j, json.dumps(j)[:300])

    r = c.get("/api/jobs/job-quick/recette"); j = J(r) if r.status_code == 200 else {}
    check("A8 recette Quick : source « quick », le prompt SAISI d'abord", j.get("source") == "quick"
          and j.get("prompt") == "le prompt SAISI" and isinstance(j.get("quick"), dict)
          and j["quick"].get("seedance", {}).get("vibe") == "glitch", json.dumps(j)[:300])
    check("A8b recette Quick : le prompt ENVOYÉ reste lisible (graphe Studio)", j.get("prompt_envoye") == "prompt construit, tags")
    check("A9 recette Quick : modèle et format du formulaire", j.get("model") == "kling-3" and j.get("aspect_ratio") == "1:1"
          and j.get("duration_s") == 10)

    r = c.get("/api/jobs/job-tpl/recette"); j = J(r) if r.status_code == 200 else {}
    check("A10 rendu de gabarit avec graphe source : studio vrai, template_id", j.get("studio") is True
          and j.get("template_id") == "tpl-3" and j.get("source") == "job", json.dumps(j)[:200])
    check("A11 job inconnu : 404", c.get("/api/jobs/inconnu/recette").status_code == 404)
    check("A12 /recipe historique inchangé (404 sans recette Quick)", c.get("/api/jobs/job-api/recipe").status_code == 404
          and J(c.get("/api/jobs/job-quick/recipe")).get("tab") == "seedance")

    print("\n[B] import : recette jointe ou posée à côté")
    import subprocess, shutil
    ff = shutil.which("ffmpeg") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
    if os.path.isfile(ff) and os.path.dirname(ff) not in os.environ["PATH"]:
        os.environ["PATH"] = os.path.dirname(ff) + os.pathsep + os.environ["PATH"]
    clip = pathlib.Path(TMP) / "src.mp4"
    subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=64x64:r=10:d=1", "-pix_fmt",
                    "yuv420p", str(clip)], check=True)
    data = clip.read_bytes()
    REC = {"source": "HyperFrames", "composition": "dvg-mix60s", "variables": {"lang": "fr", "couche": "plans"},
           "clips": [{"job_id": "9ba81b30", "prompt": "The giant bioluminescent jellyfish…"},
                     {"job_id": "3cba8ed2", "prompt": "The white sneakers spin…"}]}
    r = c.post("/api/videos/upload", files={"file": ("mix_fr.mp4", data, "video/mp4")},
               data={"recette": json.dumps(REC)})
    jid = J(r).get("job_id") if r.status_code == 200 else None
    check("B1 upload avec recette : 200", r.status_code == 200 and jid, r.text[:200])
    j = J(c.get(f"/api/jobs/{jid}/recette")) if jid else {}
    check("B2 la recette d'import est rendue (source « import »)", j.get("source") == "import"
          and j.get("import", {}).get("composition") == "dvg-mix60s"
          and j["import"]["clips"][0]["prompt"].startswith("The giant"), json.dumps(j)[:300])
    check("B3 un import sans prompt propre n'invente rien (ni prompt, ni modèle, ni le 9:16 écrit en dur à l'upload)",
          j.get("prompt") in (None, "") and j.get("model") in (None, "") and j.get("aspect_ratio") is None, json.dumps(j)[:200])
    r = c.post("/api/videos/upload", files={"file": ("bad.mp4", data, "video/mp4")}, data={"recette": "{pas du json"})
    check("B4 recette illisible : 400, aucun fichier gardé", r.status_code == 400
          and not (settings.outputs_path / "uploads" / "bad.mp4").exists(), f"{r.status_code} {r.text[:120]}")
    r = c.post("/api/videos/upload", files={"file": ("liste.mp4", data, "video/mp4")}, data={"recette": "[1,2]"})
    check("B5 recette qui n'est pas un objet : 400", r.status_code == 400, str(r.status_code))
    r = c.post("/api/videos/upload", files={"file": ("gros.mp4", data, "video/mp4")},
               data={"recette": json.dumps({"x": "a" * 70000})})
    check("B6 recette > 64 Ko : 400", r.status_code == 400, str(r.status_code))
    r = c.post("/api/videos/upload", files={"file": ("nue.mp4", data, "video/mp4")})
    jn = J(r).get("job_id") if r.status_code == 200 else None
    jr = J(c.get(f"/api/jobs/{jn}/recette")) if jn else {}
    check("B7 import sans recette : 200, source « aucune »", r.status_code == 200 and jr.get("source") == "aucune"
          and jr.get("import") is None, json.dumps(jr)[:200])
    side = settings.outputs_path / "uploads" / "nue.recette.json"
    side.write_text(json.dumps({"source": "HyperFrames", "composition": "posee-a-cote"}), encoding="utf-8")
    jr = J(c.get(f"/api/jobs/{jn}/recette")) if jn else {}
    check("B8 fichier <nom>.recette.json posé à côté : lu", jr.get("source") == "import"
          and jr.get("import", {}).get("composition") == "posee-a-cote", json.dumps(jr)[:200])

    print("\n[C] fiche audio : le prompt gardé par Son & VFX")
    aud = sfx_service._audio_dir(); aud.mkdir(parents=True, exist_ok=True)
    subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=d=1", str(aud / "musique_t283.mp3")], check=True)
    sfx_service.record_meta("musique_t283.mp3", {"kind": "musique", "prompt": "trailer 128 BPM, synthés", "model":
                                                 "lyria-3", "provider": "fal", "dur": 30})
    r = c.get("/api/library/fiche/musique_t283.mp3"); f = J(r) if r.status_code == 200 else {}
    rec = f.get("recette") or {}
    check("C1 la fiche audio montre le prompt et le modèle", r.status_code == 200 and rec.get("prompt") ==
          "trailer 128 BPM, synthés" and rec.get("model") == "lyria-3" and rec.get("origine") == "son-vfx",
          json.dumps(f)[:300])
    check("C2 rien à « rejouer » pour un son (route d'images seulement)", f.get("rejouer") is None)
    subprocess.run([ff, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=d=1", str(aud / "stem_t283.mp3")], check=True)
    sfx_service.record_meta("stem_t283.mp3", {"kind": "stem", "source": "x.mp3"})
    f2 = J(c.get("/api/library/fiche/stem_t283.mp3"))
    check("C3 un son sans prompt n'a pas de recette", f2.get("recette") is None, json.dumps(f2.get("recette")))

print("\n[D] écran : maillon dzrecette")
B = (REPO / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")
try:
    import patch_bundle_dzrecette as PR
except ImportError as e:
    PR = None
    check("D0 le maillon patch_bundle_dzrecette existe", False, repr(e))
if PR:
    check("D1 marqueur ×1", B.count(PR.MARKER) == 1, str(B.count(PR.MARKER)))
    check("D2 aller-retour exact", lambda: PR.appliquer(PR.defaire(B)) == B)
    import _i18n_l1_aide as AIDE
    check("D3 avant_dzsonvfx défait dzrecette d'abord", lambda: PR.MARKER not in AIDE.avant_dzsonvfx(B))
check("D4 comptes figés : x.useState( 731, DzTracks 181, v2.8.0 ×4",
      B.count("x.useState(") == 731 and B.count("DzTracks") == 181 and B.count("v2.8.0") == 4,
      f"{B.count('x.useState(')} {B.count('DzTracks')} {B.count('v2.8.0')}")
RAW = (REPO / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes()
check("D5 CRLF partout", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
check("D6 Envoyer vers : Quick et Studio refaire pour un rendu",
      'lbl:dzT("recette.envoyer.quick")' in B and 'lbl:dzT("recette.envoyer.studio")' in B
      and "__dzRecetteQuick(m.jobId,!1)" in B and "__dzRecetteStudio(m.jobId,!1)" in B)
check("D7 la fiche d'un rendu porte le panneau de recette", "r.jsx(DzSemblables,{m:m,liste:l,ouvrir:y}),r.jsx(DzRecetteRendu,{m:m,fermer:()=>y(null)}),r.jsx(DzRecetteExport,{m:m}),m.kind===" in B)   # t346 : + le bouton « Exporter la recette »
check("D8 la recette unifiée est lue par /recette", 'fetch("/api/jobs/"+encodeURIComponent(id)+"/recette")' in B)
check("D9 graine neuve par défaut, reprise sur demande", "garder?rc.seed:__dzGraineNeuve()" in B)
check("D10 le graphe Studio : Image → Seedance, Prompt → Seedance, Seedance → Render",
      'toPort:"image"' in B and 'type:"Prompt"' in B and 'fromPort:"out",to:"sd1",toPort:"prompt"' in B)
check("D11 aucun .bak_dzrecette laissé", not list((REPO / "frontend" / "dist" / "assets").glob("*.bak_dzrecette")))
DICO = json.loads((REPO / "frontend" / "shared" / "i18n" / "recette.json").read_text(encoding="utf-8")) \
    if (REPO / "frontend" / "shared" / "i18n" / "recette.json").exists() else {}
import re
# toutes les clés posées par le maillon, ternaires comprises (« garder?"recette.toast.x":"recette.toast.y" »)
cles = set(re.findall(r'"(recette\.[a-z0-9_]+\.[a-z0-9_]+)"', B))
# la source est composée à l'exécution (dzT("recette.source."+rc.source)) : ses quatre valeurs serveur, une par une
cles |= {"recette.source." + v for v in ("quick", "job", "import", "aucune")}
check("D13 clés à trois segments (zone.objet.role)", all(k.count(".") == 2 for k in cles), sorted(cles)[:5])
check("D12 toutes les clés recette.* du bundle sont traduites FR et EN", cles and all(
    k in DICO and DICO[k].get("fr") and DICO[k].get("en") for k in cles), sorted(k for k in cles if k not in DICO))
ASSEMB = (REPO / "frontend" / "shared" / "i18n" / "_dz_i18n.json")
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
