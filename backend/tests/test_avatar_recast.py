# -*- coding: utf-8 -*-
"""Avatar live G1 (t162, 10/10/2026) — le Recast différé (équivalent de Genjutsu) : une vidéo de 3 à 30 s + un
Personnage -> un JOB rendu par fal (Wan Animate replace/move, Kling v3 Motion Control, Lucy Edit Pro).

Sur de VRAIS fichiers (mp4 écrits par ffmpeg, mesurés par ffprobe). AUCUN appel fal : upload, subscribe et
téléchargement sont des espions. Les corps fal sont ceux de l'openapi de queue relevé le 10/10 (spec §9). La route
payante passe la garde des plafonds AVANT tout envoi (402 sans upload) ; confirmée, le job naît (provider recast,
lignée parent_job_id), se rend, et le registre porte le devis.
Run (depuis backend/) : & $PY tests/test_avatar_recast.py"""
import base64, io, os, pathlib, shutil, subprocess, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzrecast_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


FFMPEG = shutil.which("ffmpeg") or os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")


def mp4(nom, secs, w=720, h=1280):
    p = _tmp / nom
    subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate=24:duration={secs}",
                    "-pix_fmt", "yuv420p", str(p)], check=True, timeout=180)
    return p


def png(w=600, h=600, c=(200, 80, 40)):
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (w, h), c).save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import recast_service as RS, pricing, plafonds, avatar_live as AL   # noqa: E402

UPLOADS, APPELS = [], []


async def f_upload(path):
    UPLOADS.append(pathlib.Path(path).name)
    return f"https://fal.test/{pathlib.Path(path).name}"


async def f_subscribe(endpoint, arguments):
    APPELS.append((endpoint, dict(arguments)))
    return {"video": {"url": "https://fal.test/sortie.mp4"}}


async def f_download(url, dest):
    shutil.copy2(SRC5, dest)

RS._upload, RS._fal_subscribe, RS._download = f_upload, f_subscribe, f_download

SRC5 = mp4("cinq.mp4", 5)
SRC40 = mp4("long.mp4", 40)
SRC2 = mp4("court.mp4", 2)
SRCSON = _tmp / "son.mp4"     # une prise AVEC sa piste son (la voix de l'acteur)
subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=720x1280:rate=24:duration=5", "-f", "lavfi",
                "-i", "sine=frequency=440:duration=5", "-shortest", "-pix_fmt", "yuv420p", "-c:a", "aac", str(SRCSON)],
               check=True, timeout=180)

print("\n[P] prix relevés le 10/10")
e = lambda **o: pricing.estimate(dict({"kind": "recast", "seconds": 10}, **o))
check("P1 Wan replace 720p : 10 s = 0,80 $ (fal)", abs(e(modele="remplacer", resolution="720p")["total_usd"] - 0.8) < 1e-6
      and e(modele="remplacer")["breakdown"][0]["provider"] == "fal", str(e(modele="remplacer")))
check("P2 Wan 480p 0,40 $ ; Kling standard 1,26 $ ; Kling pro 1,68 $ ; Lucy Edit Pro 720p 1,50 $",
      [round(e(modele=m, resolution=r)["total_usd"], 4) for m, r in
       (("remplacer", "480p"), ("mouvement", ""), ("mouvement_pro", ""), ("objet", "720p"))] == [0.4, 1.26, 1.68, 1.5])
check("P3 modèle inconnu : devis nul QUI LE DIT (ligne à 0, jamais une erreur)",
      e(modele="pirate")["total_usd"] == 0 and e(modele="pirate")["breakdown"], str(e(modele="pirate")))
check("P4 résolution inconnue -> la résolution par défaut du modèle (720p)",
      abs(e(modele="remplacer", resolution="8k")["total_usd"] - 0.8) < 1e-6)

print("\n[A] arguments fal (openapi du 10/10)")
prep = {"modele": "remplacer", "resolution": "580p", "consigne": "", "orientation": "video"}
check("A1 Wan : video_url, image_url, resolution, qualité haute",
      RS.arguments(prep, "V", ["I0", "I1"]) == {"video_url": "V", "image_url": "I0", "resolution": "580p", "video_quality": "high"})
prep = {"modele": "mouvement", "resolution": "source", "consigne": "the character on a beach", "orientation": "video"}
a = RS.arguments(prep, "V", ["I0", "I1", "I2", "I3", "I4"])
check("A2 Kling : orientation, son d'origine GARDÉ, consigne, élément visage frontal + 3 vues au plus",
      a == {"video_url": "V", "image_url": "I0", "character_orientation": "video", "keep_original_sound": True,
            "prompt": "the character on a beach",
            "elements": [{"frontal_image_url": "I0", "reference_image_urls": ["I1", "I2", "I3"]}]}, str(a))
prep = {"modele": "objet", "resolution": "720p", "consigne": "red jacket", "orientation": "video"}
check("A3 Lucy Edit : video_url, prompt, resolution — aucune image",
      RS.arguments(prep, "V", []) == {"video_url": "V", "prompt": "red jacket", "resolution": "720p"})
check("A4 préréglage + consigne pour Lucy : la consigne d'abord, le décor ensuite",
      RS.consigne_finale("objet", "red jacket", "plage").startswith("red jacket Change the background")
      and "sunset" in RS.consigne_finale("objet", "", "plage"))
check("A5 douze préréglages, ids uniques", len(RS.PREREGLAGES) == 12 and len({p["id"] for p in RS.PREREGLAGES}) == 12)

with TestClient(app, client=("127.0.0.1", 5), raise_server_exceptions=False) as loc, \
        TestClient(app, client=("192.168.1.42", 5), raise_server_exceptions=False) as lan:
    pj = loc.post("/api/avatar-live/personnages", json={"nom": "Oli", "images": [png(), png(c=(1, 2, 3))],
                                                        "consentement": True}).json()
    pid = pj["id"]

    print("\n[M] le catalogue servi")
    m = loc.get("/api/avatar-live/recast/modeles").json()
    check("M1 cinq modèles avec libellé, prix, défaut, besoin d'un Personnage ; préréglages ; bornes 3-30 s",
          set(m.get("modeles", {})) == set(RS.MODELES) and m["modeles"]["objet"]["personnage"] is False
          and len(m.get("prereglages", [])) == 12 and m.get("duree") == {"min": 3, "max": 30}, str(m)[:300])

    print("\n[S] la source déposée")
    with open(SRC5, "rb") as fh:
        r = loc.post("/api/avatar-live/recast/source", files={"fichier": ("prise.mp4", fh, "video/mp4")})
    dep = r.json().get("depot", "") if r.status_code == 200 else ""
    check("S1 dépôt d'un mp4 : nom aléatoire confiné, durée mesurée par ffprobe",
          r.status_code == 200 and RS.chemin_depot(dep) is not None and 4.5 < r.json().get("duree_s", 0) < 5.5, r.text[:200])
    r = loc.post("/api/avatar-live/recast/source", files={"fichier": ("x.mp4", b"pas une video", "video/mp4")})
    check("S2 des octets qui ne sont pas une vidéo : 415, rien gardé",
          r.status_code == 415 and len(list(RS.sources_dir().iterdir())) == 1, r.text[:200])
    r = loc.post("/api/avatar-live/recast/source", files={"fichier": ("x.exe", b"MZ", "application/octet-stream")})
    check("S3 une extension hors mp4/mov/webm : 415", r.status_code == 415, r.text[:200])
    check("S4 dépôt depuis le Wi-Fi : écriture refusée (403)",
          lan.post("/api/avatar-live/recast/source", files={"fichier": ("p.mp4", b"x", "video/mp4")},
                   headers={"Authorization": "Bearer " + "0" * 64}).status_code in (401, 403))
    (RS.sources_dir().parent / "piege.mp4").write_bytes(b"x")          # une cible RÉELLE hors du dossier des dépôts
    (RS.sources_dir() / ("a" * 24 + ".exe")).write_bytes(b"MZ")
    check("S5 un nom de dépôt piégé ne se résout pas, même vers un fichier qui existe",
          RS.chemin_depot("../piege.mp4") is None and RS.chemin_depot("..\piege.mp4") is None
          and RS.chemin_depot("a" * 24 + ".exe") is None and RS.chemin_depot(dep) is not None)
    (RS.sources_dir() / ("a" * 24 + ".exe")).unlink()

    print("\n[G] les gardes, AVANT tout envoi")
    def lancer(**corps):
        b = dict({"source": {"depot": dep}, "personnage_id": pid, "modele": "remplacer"}, **corps)
        return loc.post("/api/avatar-live/recast", json=b)
    r = lancer(modele="pirate")
    check("G1 modèle inconnu : 400 qui nomme les connus, aucun upload", r.status_code == 400 and "remplacer" in r.text
          and not UPLOADS, r.text[:200])
    r = lancer(personnage_id="inconnu")
    check("G2 Personnage manquant pour Wan : 400 qui le dit", r.status_code == 400 and "Personnage" in r.text and not UPLOADS, r.text[:200])
    r = lancer(personnage_id=None)
    check("G2b AUCUN Personnage pour Wan : 400 qui le dit, aucun upload",
          r.status_code == 400 and "Personnage" in r.text and not UPLOADS, r.text[:200])
    r = lancer(source={"depot": "f" * 24 + ".mp4"})
    check("G3 source introuvable : 404", r.status_code == 404 and not UPLOADS, r.text[:200])
    for nom, src in (("long", SRC40), ("court", SRC2)):
        with open(src, "rb") as fh:
            d = loc.post("/api/avatar-live/recast/source", files={"fichier": (f"{nom}.mp4", fh, "video/mp4")}).json()["depot"]
        r = lancer(source={"depot": d})
        check(f"G4 source {nom} : 400 qui cite la mesure et la borne 3-30 s",
              r.status_code == 400 and "30 s" in r.text and "Montage" in r.text and not UPLOADS, r.text[:200])
    r = lancer(modele="objet", personnage_id=None)
    check("G5 Lucy Edit sans consigne ni préréglage : 400", r.status_code == 400 and "consigne" in r.text, r.text[:200])
    plafonds.enregistrer({"par_moteur": {"fal": 0.10}})
    r = lancer()
    check("G6 plafond fal 0,10 $ < devis 0,40 $ : 402 dz_plafond, AUCUN upload, aucun job",
          r.status_code == 402 and "dz_plafond" in r.text and not UPLOADS
          and loc.get("/api/jobs").status_code == 200, r.text[:200])
    plafonds.enregistrer({"par_moteur": {}})
    os.environ["FAL_KEY"] = ""
    from app.config import settings
    settings.FAL_KEY = ""
    r = lancer()
    check("G7 sans clé fal : 400 qui le dit, rien lancé", r.status_code == 400 and "fal" in r.text.lower() and not UPLOADS, r.text[:200])
    settings.FAL_KEY = "test-key"

    print("\n[J] le job")
    r = lancer(resolution="720p", prereglage="plage")
    jid = r.json().get("job_id", "") if r.status_code == 200 else ""
    check("J1 lancé : job_id + devis 0,40 $ (5 s à 0,08 $/s)", r.status_code == 200 and jid
          and abs(r.json().get("devis_usd", 0) - 0.4) < 0.02, r.text[:200])
    fin = time.time() + 60
    j = {}
    while time.time() < fin:
        j = loc.get(f"/api/jobs/{jid}").json()
        if j.get("status") in ("done", "failed"):
            break
        time.sleep(0.3)
    check("J2 le job se rend : done, provider recast, modèle, durée 5 s, vidéo écrite",
          j.get("status") == "done" and j.get("provider") == "recast" and j.get("video_model") == "remplacer"
          and (_tmp / "outputs" / "final" / f"{jid}.mp4").is_file(), str(j)[:300])
    check("J3 envoyés à fal : la vidéo PUIS les deux images du Personnage ; l'endpoint Wan replace",
          len(UPLOADS) == 3 and UPLOADS[0].endswith(".mp4") and UPLOADS[1:] == ["ref_0.png", "ref_1.png"]
          and APPELS[-1][0] == "fal-ai/wan/v2.2-14b/animate/replace", str(UPLOADS) + str(APPELS[-1:]))
    import asyncio                                                   # noqa: E402
    lg = [l for l in asyncio.run(plafonds.tableau())["lignes"] if l["moteur"] == "fal"]
    check("J4 le devis est au registre, catégorie studio", lg and lg[0]["categorie"] == "studio"
          and abs(lg[0]["estime_usd"] - 0.4) < 0.02, str(lg))

    print("\n[L] la lignée depuis un rendu")
    from app.services.storage import JobRecord, async_session_factory   # noqa: E402
    async def parent():
        async with async_session_factory() as s:
            s.add(JobRecord(id="parent-1", status="done", image_filename="", final_video_path=str(SRC5)))
            await s.commit()
    asyncio.run(parent())
    r = lancer(source={"job_id": "parent-1"}, modele="mouvement", consigne="on stage")
    jid2 = r.json().get("job_id", "")
    fin = time.time() + 60
    while time.time() < fin and loc.get(f"/api/jobs/{jid2}").json().get("status") not in ("done", "failed"):
        time.sleep(0.3)
    async def lire():
        async with async_session_factory() as s:
            return await s.get(JobRecord, jid2)
    jr = asyncio.run(lire())
    check("L1 depuis un rendu : parent_job_id posé, Kling standard appelé avec la consigne",
          jr is not None and jr.parent_job_id == "parent-1" and APPELS[-1][0].endswith("v3/standard/motion-control")
          and APPELS[-1][1].get("prompt") == "on stage", str(APPELS[-1:]))

    async def f_vide(endpoint, arguments):
        return {"oops": 1}
    RS._fal_subscribe = f_vide
    r = lancer()
    jid3 = r.json().get("job_id", "")
    fin = time.time() + 60
    while time.time() < fin and (j := loc.get(f"/api/jobs/{jid3}").json()).get("status") not in ("done", "failed"):
        time.sleep(0.3)
    check("L2 fal répond sans vidéo : job failed qui nomme les clés reçues", j.get("status") == "failed"
          and "oops" in (j.get("error") or ""), str(j)[:200])

    print("\n[A] le son de la source est gardé (Genjutsu garde l'audio et les lèvres)")
    RS._fal_subscribe = f_subscribe
    with open(SRCSON, "rb") as fh:
        dson = loc.post("/api/avatar-live/recast/source", files={"fichier": ("son.mp4", fh, "video/mp4")}).json()["depot"]
    r = lancer(source={"depot": dson})
    jid4 = r.json().get("job_id", "")
    fin = time.time() + 60
    while time.time() < fin and (j := loc.get(f"/api/jobs/{jid4}").json()).get("status") not in ("done", "failed"):
        time.sleep(0.3)
    sortie = _tmp / "outputs" / "final" / f"{jid4}.mp4"
    check("SON1 fal rend une vidéo MUETTE, la source parle : la sortie porte la piste de la source",
          j.get("status") == "done" and RS.a_du_son(sortie), str(j)[:200])
    check("SON2 témoin : la sortie simulée de fal n'avait pas de son", not RS.a_du_son(SRC5))
    check("SON3 source muette : sortie muette, aucun échec (rendu J2)", not RS.a_du_son(_tmp / "outputs" / "final" / f"{jid}.mp4"))

    print("\n[T] le téléphone appairé (G6)")
    from app.services import appairage                                # noqa: E402
    jeton, _ = asyncio.run(appairage.reclamer(appairage.creer_secret().secret, "Pixel"))
    H = {"Authorization": "Bearer " + jeton}
    with open(SRC5, "rb") as fh:
        r = lan.post("/api/avatar-live/recast/source", files={"fichier": ("tel.mp4", fh, "video/mp4")}, headers=H)
    dtel = r.json().get("depot", "") if r.status_code == 200 else ""
    check("T1 le téléphone dépose sa prise (écriture ouverte, vérifiée par ffprobe comme sur le PC)",
          r.status_code == 200 and RS.chemin_depot(dtel) is not None, r.text[:200])
    RS._fal_subscribe = f_subscribe
    plafonds.enregistrer({"par_moteur": {"fal": 0.0001}})
    r = lan.post("/api/avatar-live/recast", json={"source": {"depot": dtel}, "personnage_id": pid, "modele": "remplacer"},
                 headers=H)
    check("T2 ...et lance un Recast : la MÊME garde du plafond le refuse (402) avant tout envoi",
          r.status_code == 402 and "dz_plafond" in r.text, r.text[:200])
    plafonds.enregistrer({"par_moteur": {}})
    r = lan.post("/api/avatar-live/recast", json={"source": {"depot": dtel}, "personnage_id": pid, "modele": "remplacer"},
                 headers=H)
    check("T3 sous le plafond : le job part depuis le téléphone", r.status_code == 200 and r.json().get("job_id"), r.text[:200])
    check("T4 sans jeton depuis le Wi-Fi : 401, rien", lan.post("/api/avatar-live/recast", json={}).status_code == 401)
    check("T5 créer un Personnage reste réservé au PC (le consentement se donne là)",
          lan.post("/api/avatar-live/personnages", json={"nom": "x", "images": [png()], "consentement": True},
                   headers=H).status_code == 403)

print("\n[R] recensement")
import _recensement_payant as RP                                    # noqa: E402
rec = RP.recenser()
k = ("avatar_live", "POST", "/recast")
check("R1 /recast atteint un puits ET appelle la garde", k in rec and rec[k]["puits"] and rec[k]["garde"], str(rec.get(k)))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
