# -*- coding: utf-8 -*-
"""t511 (RV1, 26/11/2026) — banc de la matière « vidéo » de l'Inspiration (étages 0 et 1 gratuits, purge R4).

Sections :
  1. fonctions pures : lire_sonde (rotation), lire_son (muet sous -60 dB), lire_plans (volets regroupés), cadre,
     rythme, boucle_depuis_images (période trouvée / pas de répétition), fiche (calculée sur la période), echeance ;
  2. vraie vidéo fabriquée par ffmpeg (trois plans, son) : POST /api/inspiration/video -> fiche (9:16, 3 plans, son),
     planches servies, aucun nom interne exposé ; vidéo muette -> son faux ; liste : matière et fiche ;
  3. refus : extension (400 format), fichier illisible (400 illisible, dossier effacé), garde locale (403),
     planche hors registre (404) ;
  4. purge R4 : à l'échéance la vidéo et les planches disparaissent, la fiche reste, planche -> 410 ;
  5. traduction L10 des messages neufs (Accept-Language: en).
ffmpeg et ffprobe doivent être sur le PATH (ceux de l'app ou de C:\\ffmpeg) ; sinon la section 2 est sautée et le dit.
Run (depuis backend/) : & $PY tests/test_inspiration_video.py"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzinsv_"))
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

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from app.services import inspiration_video as IV                    # noqa: E402
from app.services import inspiration as I                           # noqa: E402


def section_pures():
    print("[1] fonctions pures")
    s = IV.lire_sonde(json.dumps({"format": {"duration": "42.87"}, "streams": [
        {"codec_type": "video", "width": 1920, "height": 1080, "avg_frame_rate": "30000/1001", "codec_name": "h264",
         "side_data_list": [{"rotation": -90}]}, {"codec_type": "audio"}]}))
    check("1a sonde : rotation -90 échange largeur et hauteur", (s["largeur"], s["hauteur"]) == (1080, 1920), s)
    check("1b sonde : durée, cadence, son", s["duree_s"] == 42.87 and s["images_par_s"] == 29.97 and s["piste_audio"], s)
    check("1c sonde illisible -> durée 0", IV.lire_sonde("pas du json")["duree_s"] == 0)
    son = IV.lire_son("silence_start: 1.5\nsilence_end: 2.25 | silence_duration: 0.75\n"
                      "mean_volume: -22.4 dB\nmax_volume: -3.1 dB\n")
    check("1d son : niveaux et silences", son["niveau_max_db"] == -3.1 and son["silences"] == [[1.5, 2.25]]
          and not son["muet"], son)
    check("1e son sous -60 dB de crête -> muet", IV.lire_son("max_volume: -91.0 dB")["muet"])
    check("1f son sans mesure -> muet", IV.lire_son("")["muet"])
    p = IV.lire_plans("pts_time:2.0 x\npts_time:2.1\npts_time:2.2\npts_time:5.5\npts_time:0\n")
    check("1g plans : volet de 3 coupes en < 0,4 s = une coupe", p["coupes_s"] == [2.0, 5.5] and p["volets_s"] == [2.0], p)
    check("1h cadre 1080×1920 = 9:16 ; 1080×1350 = 4:5 ; 1000×700 = libre",
          IV.cadre(1080, 1920) == "9:16" and IV.cadre(1080, 1350) == "4:5" and IV.cadre(1000, 700) == "1000×700")
    check("1i cadre inconnu -> vide", IV.cadre(None, 10) == "" and IV.cadre(0, 10) == "")
    r = IV.rythme([2.0, 5.0], 8.0)
    check("1j rythme : 3 plans 2/3/3 s", r["plans"] == 3 and r["duree_min_s"] == 2.0 and r["duree_max_s"] == 3.0
          and r["plans_par_minute"] == 22.5, r)
    check("1k rythme sans durée -> 0 plan", IV.rythme([], 0)["plans"] == 0)
    # boucle : 10 s de motif répété 3 fois à 2 i/s (60 images), images distinctes dans le motif
    motif = [bytes([(i * 37 + k) % 256 for k in range(16)]) for i in range(20)]
    b = IV.boucle_depuis_images(motif * 3 + motif[:10], 2, 35.0)
    check("1l boucle : période 10 s trouvée", b and b["repetee"] and b["periode_s"] == 10.0, b)
    import random
    random.seed(4)
    bruit = [bytes(random.randrange(256) for _ in range(16)) for _ in range(60)]
    b2 = IV.boucle_depuis_images(bruit, 2, 30.0)
    check("1m pas de répétition -> periode None", b2 is not None and b2["periode_s"] is None, b2)
    check("1n moins de 12 s d'images -> None", IV.boucle_depuis_images(motif, 2, 10.0) is None)
    f = IV.fiche({"duree_s": 30.0, "largeur": 1080, "hauteur": 1920, "images_par_s": 30, "piste_audio": True},
                 {"muet": False, "silences": [[1, 2], [12, 13]]}, {"coupes_s": [3.0, 6.0, 13.0, 16.0]},
                 {"periode_s": 10.0})
    check("1o fiche sur la période : 10 s, 3 plans, boucle, son, 1 silence",
          f["format"]["duree_s"] == 10.0 and f["format"]["duree_fichier_s"] == 30.0 and f["rythme"]["plans"] == 3
          and f["format"]["boucle"] and f["format"]["son"] and f["silences"] == 1 and f["format"]["cadre"] == "9:16", f)
    check("1p fiche : piste audio muette -> son faux",
          not IV.fiche({"duree_s": 5, "piste_audio": True}, {"muet": True}, {}, None)["format"]["son"])
    check("1q échéance à 7 jours", IV.echeance("2026-11-26T10:00:00+00:00") == "2026-12-03T10:00:00+00:00")
    check("1r aucune phrase de la source dans la fiche (que des nombres et des drapeaux)",
          all(not isinstance(v, str) or v in ("9:16",) for v in f["format"].values()))


def ffmpeg_present():
    return shutil.which("ffmpeg") and shutil.which("ffprobe")


def fabriquer(dossier: pathlib.Path, nom: str, son: bool) -> pathlib.Path:
    """Trois plans de 2 s (couleurs pleines différentes) en 270×480, avec ou sans un son de 440 Hz."""
    out = dossier / nom
    entrees = []
    for c in ("red", "blue", "green"):
        entrees += ["-f", "lavfi", "-i", f"color=c={c}:s=270x480:r=25:d=2"]
    filtre = "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *entrees]
    if son:
        cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=6"]
    cmd += ["-filter_complex", filtre, "-map", "[v]"]
    if son:
        cmd += ["-map", "3:a", "-c:a", "aac"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "6", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def section_routes():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import espaces
    with TestClient(app, client=("127.0.0.1", 50000)) as client, \
            TestClient(app, client=("192.168.1.20", 50000)) as dehors:
        EA = espaces.creer({"nom": "Studio Réf"})["id"]
        H = {"X-Dz-Espace": EA}
        print("[3] refus")
        r = dehors.post("/api/inspiration/video", files={"video": ("a.mp4", b"x", "video/mp4")})
        check("3a hors machine -> 401 ou 403", r.status_code in (401, 403), r.status_code)
        r = client.post("/api/inspiration/video", headers=H, files={"video": ("a.gif", b"GIF89a", "image/gif")})
        check("3b extension refusée -> 400 format", r.status_code == 400 and r.json()["detail"]["code"] == "format", r.text[:200])
        avant = set(p.name for p in (_tmp / "inspirations").glob("*")) if (_tmp / "inspirations").exists() else set()
        r = client.post("/api/inspiration/video", headers=H, files={"video": ("a.mp4", b"pas une video" * 10, "video/mp4")})
        apres = set(p.name for p in (_tmp / "inspirations").glob("*"))
        check("3c fichier illisible -> 400 illisible", r.status_code == 400 and r.json()["detail"]["code"] == "illisible",
              r.text[:200])
        check("3d dossier effacé après le refus", apres == avant, apres - avant)
        r = client.post("/api/inspiration/video", headers={**H, "Accept-Language": "en"},
                        files={"video": ("a.gif", b"GIF89a", "image/gif")})
        check("5a message traduit en anglais", "Video expected" in r.text, r.text[:200])

        if not ffmpeg_present():
            print("  SAUTÉ section 2 et 4 : ffmpeg ou ffprobe absent du PATH")
            return
        print("[2] vraie vidéo")
        src = fabriquer(_tmp, "trois_plans.mp4", son=True)
        r = client.post("/api/inspiration/video", headers=H, data={"source_libelle": "Reel vu", "source_lien": "https://x.example/r"},
                        files={"video": ("ref.mp4", src.read_bytes(), "video/mp4")})
        check("2a 200", r.status_code == 200, r.text[:300])
        j = r.json() if r.status_code == 200 else {}
        v = j.get("video") or {}
        fi = v.get("fiche") or {}
        check("2b matière vidéo, cadre 9:16, ~6 s", j.get("matiere") == "video" and fi.get("format", {}).get("cadre") == "9:16"
              and abs(fi.get("format", {}).get("duree_s", 0) - 6.0) < 0.2, fi)
        check("2c trois plans", fi.get("rythme", {}).get("plans") == 3, fi.get("rythme"))
        check("2d son présent", fi.get("format", {}).get("son") is True and v.get("etage0", {}).get("son") is True, v.get("etage0"))
        check("2e planches produites", len(v.get("planches") or []) >= 1, v.get("planches"))
        check("2f nom interne du fichier non exposé", "source.mp4" not in json.dumps(j.get("source")), j.get("source"))
        check("2g échéance de purge à 7 jours", v.get("purge_le") == IV.echeance(v.get("analyse_le")), v.get("purge_le"))
        IID = j.get("id")
        if v.get("planches"):
            r = client.get(f"/api/inspiration/{IID}/planches/{v['planches'][0]}", headers=H)
            check("2h planche servie en JPEG", r.status_code == 200 and r.content[:2] == b"\xff\xd8", r.status_code)
        r = client.get(f"/api/inspiration/{IID}/planches/vues_99.jpg", headers=H)
        check("3e planche hors registre -> 404", r.status_code == 404, r.status_code)
        r = client.get(f"/api/inspiration/{IID}/planches/..%5Cinspiration.json", headers=H)
        check("3f chemin glissé dans le nom -> 404", r.status_code == 404, r.status_code)
        muette = fabriquer(_tmp, "muette.mp4", son=False)
        r = client.post("/api/inspiration/video", headers=H, files={"video": ("m.mp4", muette.read_bytes(), "video/mp4")})
        check("2i vidéo sans piste -> son faux", r.status_code == 200 and r.json()["video"]["fiche"]["format"]["son"] is False,
              r.text[:200])
        r = client.get("/api/inspiration", headers=H)
        el = next((x for x in r.json().get("inspirations", []) if x["id"] == IID), {})
        check("2j liste : matière et fiche", el.get("matiere") == "video" and el.get("fiche", {}).get("rythme", {}).get("plans") == 3,
              el)

        print("[4] purge R4")
        d = _tmp / "inspirations" / IID
        check("4a avant l'échéance : rien n'est effacé", IV.purger() == 0 and (d / "source.mp4").exists())
        n = IV.purger(datetime.now(timezone.utc) + timedelta(days=8))
        rec = I.lire(IID)
        check("4b après : vidéo et planches effacées", n >= 1 and not (d / "source.mp4").exists()
              and not (d / "planches").exists(), n)
        check("4c la fiche reste, purgee vrai", rec["video"]["purgee"] and rec["video"]["fiche"]["rythme"]["plans"] == 3)
        r = client.get(f"/api/inspiration/{IID}/planches/{v['planches'][0]}", headers=H)
        check("4d planche après la purge -> 410", r.status_code == 410, r.status_code)
        check("4e purge idempotente", IV.purger(datetime.now(timezone.utc) + timedelta(days=9)) == 0)


def test_inspiration_video():
    section_pures()
    section_routes()
    assert fail == 0, f"{fail} échec(s)"


if __name__ == "__main__":
    try:
        section_pures()
        section_routes()
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
