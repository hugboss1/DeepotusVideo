# -*- coding: utf-8 -*-
"""t317 (28/10/2026) (D3, tâches 1 et 2) — banc du service app/services/capture_montage.py (montage après coup).
Plan docs/superpowers/plans/2026-10-28-t317-montage-capture.md, spec boîte à outils §8.4.
  [P] proposition d'après la piste des clics : zooms groupés, clic secret ignoré, coupes des générations, chapitres ;
  [V] validation (liste blanche, bornes, chevauchements, coupe pleine durée refusée) ;
  [T] temps de sortie (segments, coupes retirées ou accélérées), chapitres remappés, texte « 00:00 », FFMETADATA ;
  [Z] zoom_a (1 hors zooms, k au milieu, rampe douce) et expressions ffmpeg évaluées = zoom_a ;
  [R] rendu ffmpeg réel sur une fausse capture (WebM sans durée) : remux, tailles des formats, durées, chapitres,
      zoom visible, source muette.
Données jetables, aucun réseau. Run (depuis backend/) : & $PY tests/test_capture_montage_service.py"""
import json, math, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcapmont_"))
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
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {str(detail)[:500]}")


from app.services import capture_montage as M                      # noqa: E402


def clic(t, x, y, ecran="quick", secret=False, fiche=None):
    c = {"type": "clic", "t": t, "x": x, "y": y, "bouton": 0, "ecran": ecran,
         "cible": {"balise": "button", "role": "", "t": "Générer", "i": ""}, "fiche": fiche}
    if secret:
        c["secret"] = True
    return c


PISTE = {"version": 1, "id": "a" * 16, "duree_ms": 60000, "cadre": {"largeur": 1440, "hauteur": 900, "mode": "app"},
         "evenements": sorted([
             {"type": "ecran", "t": 0, "ecran": "quick"},
             clic(2000, 0.30, 0.40), clic(2600, 0.32, 0.42), clic(3500, 0.34, 0.38),       # un geste -> un zoom
             clic(9000, 0.90, 0.10),                                                         # loin -> un autre
             clic(9400, 0.20, 0.80),                                                         # proche en temps, loin en place
             clic(15000, 0.5, 0.5, secret=True),                                             # secret : jamais zoomé
             {"type": "generation_debut", "t": 20000, "job_id": "j1", "provider": "fal"},
             {"type": "generation_fin", "t": 30000, "job_id": "j1", "provider": "fal", "statut": "done"},
             {"type": "generation_debut", "t": 31000, "job_id": "j2", "provider": "fal"},
             {"type": "generation_fin", "t": 33000, "job_id": "j2", "provider": "fal", "statut": "done"},
             {"type": "ecran", "t": 40000, "ecran": "studio"},
             {"type": "ecran", "t": 48000, "ecran": "library"},                              # < 3 s : absorbé
             {"type": "ecran", "t": 50000, "ecran": "montage"},
         ], key=lambda e: e["t"])}

print("[P] proposition")
P = M.proposer(PISTE)
Z = P["zooms"]
check("P1 version, format 16:9 par défaut, sous-titres aucun", P["version"] == 1 and P["format"] == "16:9"
      and P["sous_titres"]["source"] == "aucun" and P["capture_id"] == "a" * 16, P)
check("P2 trois clics proches -> un zoom (centre moyen, fenêtre -500/+1500)", Z[0]["t0"] == 1500 and Z[0]["t1"] == 5000
      and abs(Z[0]["x"] - 0.32) < 1e-6 and abs(Z[0]["y"] - 0.40) < 1e-6, Z[:1])
check("P3 deux clics proches en temps mais loin en place -> deux zooms sans chevauchement", len(Z) == 3
      and Z[1]["t1"] <= Z[2]["t0"] and abs(Z[2]["x"] - 0.20) < 1e-6, Z)
check("P4 clic secret jamais zoomé", all(not (z["t0"] <= 15000 <= z["t1"]) for z in Z), Z)
check("P5 k par défaut 1,8 ; ids uniques", all(z["k"] == 1.8 for z in Z) and len({z["id"] for z in Z}) == len(Z), Z)
check("P6 k du skin borné (3 -> 2,5 ; 0,5 -> 1,1)", M.proposer(PISTE, k=3)["zooms"][0]["k"] == 2.5
      and M.proposer(PISTE, k=0.5)["zooms"][0]["k"] == 1.1)
C_ = P["coupes"]
check("P7 génération de 10 s -> coupe accélérée ×8 [debut+500, fin-500] ; 2 s ignorée", len(C_) == 1
      and C_[0]["t0"] == 20500 and C_[0]["t1"] == 29500 and C_[0]["mode"] == "accelerer" and C_[0]["vitesse"] == 8, C_)
CH = P["chapitres"]
check("P8 chapitres : 0 quick, 40 s studio, 50 s montage (library < 3 s absorbé)",
      [(c["t"], c["ecran"]) for c in CH] == [(0, "quick"), (40000, "studio"), (50000, "montage")], CH)
check("P9 titres vides (l'écran les nomme)", all(c["titre"] == "" for c in CH))
long_ = {"duree_ms": 30000, "evenements": [clic(1000 + i * 600, 0.5, 0.5) for i in range(30)]}
check("P10 zoom borné à 8 s (geste continu découpé)", all(z["t1"] - z["t0"] <= 8000 for z in M.proposer(long_)["zooms"])
      and len(M.proposer(long_)["zooms"]) >= 2)
vide = M.proposer({"duree_ms": 5000, "evenements": []})
check("P11 piste vide -> rien à zoomer, un chapitre à 0", vide["zooms"] == [] and vide["coupes"] == []
      and [c["t"] for c in vide["chapitres"]] == [0], vide)
check("P12 piste illisible -> proposition vide", M.proposer(None)["zooms"] == [] and M.proposer("x")["coupes"] == [])

print("[V] validation")
V = M.valider(dict(P, inconnu=1, zooms=P["zooms"] + [{"id": "z9", "t0": 4000, "t1": 7000, "k": 2, "x": 2, "y": -1,
                                                       "pirate": "<script>"}]), 60000, "a" * 16)
check("V1 champ inconnu retiré", "inconnu" not in V and all("pirate" not in z for z in V["zooms"]))
check("V2 x, y bornés 0..1 ; chevauchement rogné (zoom suivant commence à la fin du précédent)",
      all(0 <= z["x"] <= 1 and 0 <= z["y"] <= 1 for z in V["zooms"])
      and all(a["t1"] <= b["t0"] for a, b in zip(V["zooms"], V["zooms"][1:])), V["zooms"])
def refus(m, duree=60000):
    try:
        M.valider(m, duree, "a" * 16)
    except M.RefusMontage as e:
        return e.statut
    return None
check("V3 NaN / booléen / texte pour un temps -> élément retiré", len(M.valider(dict(P, zooms=[
    {"id": "a", "t0": float("nan"), "t1": 3000, "k": 2, "x": .5, "y": .5},
    {"id": "b", "t0": True, "t1": 3000, "k": 2, "x": .5, "y": .5},
    {"id": "c", "t0": "1", "t1": 3000, "k": 2, "x": .5, "y": .5}]), 60000, "a" * 16)["zooms"]) == 0)
check("V4 temps bornés à la durée, t1 > t0 + 200 sinon retiré", M.valider(dict(P, zooms=[
    {"id": "a", "t0": 59000, "t1": 99000, "k": 2, "x": .5, "y": .5},
    {"id": "b", "t0": 1000, "t1": 1100, "k": 2, "x": .5, "y": .5}]), 60000, "a" * 16)["zooms"]
      == [{"id": "a", "t0": 59000, "t1": 60000, "k": 2.0, "x": 0.5, "y": 0.5}])
check("V5 coupe qui couvre toute la durée -> 400", refus(dict(P, coupes=[{"id": "c", "t0": 0, "t1": 60000,
                                                                          "mode": "couper", "vitesse": 8}])) == 400)
check("V6 coupes chevauchantes de même mode fusionnées ; vitesse hors liste -> 8 ; mode inconnu -> accelerer",
      M.valider(dict(P, coupes=[{"id": "c1", "t0": 1000, "t1": 5000, "mode": "x", "vitesse": 3},
                                {"id": "c2", "t0": 4000, "t1": 6000, "mode": "accelerer", "vitesse": 8}]),
                60000, "a" * 16)["coupes"] == [{"id": "c1", "t0": 1000, "t1": 6000, "mode": "accelerer", "vitesse": 8}])
check("V12 coupes chevauchantes de modes différents : la seconde rognée, jamais fondue",
      M.valider(dict(P, coupes=[{"id": "c1", "t0": 1000, "t1": 5000, "mode": "accelerer", "vitesse": 8},
                                {"id": "c2", "t0": 4000, "t1": 9000, "mode": "couper", "vitesse": 8}]),
                60000, "a" * 16)["coupes"] == [{"id": "c1", "t0": 1000, "t1": 5000, "mode": "accelerer", "vitesse": 8},
                                               {"id": "c2", "t0": 5000, "t1": 9000, "mode": "couper", "vitesse": 8}])
check("V7 titre nettoyé (contrôles ôtés, 80 car.)", M.valider(dict(P, chapitres=[{"id": "h", "t": 0,
      "titre": "A\x00\x1b" + "b" * 200, "ecran": "Quick!"}]), 60000, "a" * 16)["chapitres"][0]
      == {"id": "h", "t": 0, "titre": "A" + "b" * 79, "ecran": ""})
check("V8 format inconnu -> 16:9 ; source de sous-titres inconnue -> aucun ; texte borné",
      M.valider(dict(P, format="4:3", sous_titres={"source": "x", "texte": "a" * 30000, "langue": "de"}), 60000,
                "a" * 16)["format"] == "16:9"
      and M.valider(dict(P, sous_titres={"source": "x"}), 60000, "a" * 16)["sous_titres"]["source"] == "aucun"
      and len(M.valider(dict(P, sous_titres={"source": "texte", "texte": "a" * 30000}), 60000,
                        "a" * 16)["sous_titres"]["texte"]) == 20000)
check("V9 montage illisible -> 400", refus("x") == 400 and refus(None) == 400)
check("V10 trop d'éléments bornés (200 zooms)", len(M.valider(dict(P, zooms=[
    {"id": f"z{i}", "t0": i * 250, "t1": i * 250 + 240, "k": 2, "x": .5, "y": .5} for i in range(239)]),
    60000, "a" * 16)["zooms"]) == 200)
check("V11 capture_id posé par le serveur", M.valider(dict(P, capture_id="b" * 16), 60000, "a" * 16)["capture_id"]
      == "a" * 16)

print("[T] temps de sortie")
m = M.valider(dict(P, coupes=[{"id": "c1", "t0": 10000, "t1": 18000, "mode": "accelerer", "vitesse": 8},
                              {"id": "c2", "t0": 30000, "t1": 40000, "mode": "couper", "vitesse": 8}]), 60000, "a" * 16)
S = M.segments(m, 60000)
check("T1 segments complémentaires", S == [(0, 10000, 1), (10000, 18000, 8), (18000, 30000, 1), (40000, 60000, 1)], S)
check("T2 vers_sortie : avant, dans l'accéléré, après, dans la coupe, fin",
      M.vers_sortie(5000, S) == 5000 and M.vers_sortie(14000, S) == 10500 and M.vers_sortie(20000, S) == 13000
      and M.vers_sortie(35000, S) == 23000 and M.vers_sortie(60000, S) == 43000)
CS = M.chapitres_sortie(dict(m, chapitres=[{"id": "a", "t": 0, "titre": "Début", "ecran": "quick"},
                                           {"id": "b", "t": 35000, "titre": "", "ecran": "studio"},
                                           {"id": "c", "t": 50000, "titre": "Fin", "ecran": "montage"}]), S)
check("T3 chapitre dans une coupe ramené au segment suivant ; titre vide -> écran", CS == [
    {"t": 0, "titre": "Début"}, {"t": 23000, "titre": "Studio"}, {"t": 33000, "titre": "Fin"}], CS)
check("T4 texte des chapitres", M.texte_chapitres(CS) == "00:00 Début\n00:23 Studio\n00:33 Fin"
      and M.texte_chapitres([{"t": 3725000, "titre": "X"}]) == "1:02:05 X")
FM = M.ffmetadata(CS, 43000)
check("T5 FFMETADATA : 3 chapitres, fins jointives, échappement", FM.startswith(";FFMETADATA1")
      and FM.count("[CHAPTER]") == 3 and "START=23000\nEND=33000" in FM and "END=43000" in FM
      and "title=a\\=b\\;c" in M.ffmetadata([{"t": 0, "titre": "a=b;c"}], 1000), FM)
check("T7 premier chapitre de sortie toujours à 00:00 (chapitre à 0 retiré)",
      M.chapitres_sortie({"chapitres": [{"id": "b", "t": 5000, "titre": "B", "ecran": ""}]}, [(0, 9000, 1)])
      == [{"t": 0, "titre": "B"}])
check("T6 sans coupe : un segment", M.segments(M.valider(dict(P, coupes=[]), 60000, "a" * 16), 60000) == [(0, 60000, 1)])

print("[Z] zoom")
mz = {"zooms": [{"id": "z", "t0": 2000, "t1": 6000, "k": 2.0, "x": 0.25, "y": 0.75}]}
check("Z1 hors zoom : 1, centre 0,5", M.zoom_a(mz, 1000) == (1.0, 0.5, 0.5) and M.zoom_a(mz, 7000) == (1.0, 0.5, 0.5))
check("Z2 milieu : k et centre", M.zoom_a(mz, 4000) == (2.0, 0.25, 0.75))
r = [M.zoom_a(mz, t)[0] for t in range(2000, 2401, 50)]
check("Z3 rampe monotone et douce (pente nulle au départ)", all(a <= b for a, b in zip(r, r[1:]))
      and r[1] - r[0] < (r[4] - r[3]), r)
EX = M.expressions(dict(P, zooms=P["zooms"]), "T")
def ev(expr, t):
    return eval(expr, {"__builtins__": {}}, {"clip": lambda v, a, b: max(a, min(b, v)),
                                              "between": lambda v, a, b: 1.0 if a <= v <= b else 0.0, "T": t})
pts = [i * 0.137 for i in range(0, 440)]
check("Z4 expressions ffmpeg (z, cx, cy) = zoom_a sur 440 instants",
      all(abs(ev(EX["z"], t) - M.zoom_a(P, t * 1000)[0]) < 1e-6 and abs(ev(EX["cx"], t) - M.zoom_a(P, t * 1000)[1]) < 1e-6
          and abs(ev(EX["cy"], t) - M.zoom_a(P, t * 1000)[2]) < 1e-6 for t in pts))
check("Z5 sans zoom : expressions constantes", M.expressions({"zooms": []}, "T") == {"z": "1", "cx": "0.5", "cy": "0.5"})

print("[R] rendu ffmpeg")
from app.services.effects_preview import ffmpeg_bin               # noqa: E402
FF = ffmpeg_bin()
FP = str(pathlib.Path(FF).with_name("ffprobe" + pathlib.Path(FF).suffix))


def sonde(p):
    j = json.loads(subprocess.run([FP, "-v", "error", "-show_streams", "-show_format", "-show_chapters", "-of", "json",
                                   str(p)], capture_output=True, text=True).stdout)
    v = [s for s in j["streams"] if s["codec_type"] == "video"][0]
    return {"l": v["width"], "h": v["height"], "d": float(j["format"].get("duration") or 0),
            "a": any(s["codec_type"] == "audio" for s in j["streams"]), "ch": j.get("chapters", [])}


def fausse_capture(cid, son=True):
    d = M.racine() / cid
    d.mkdir(parents=True)
    # un WebM « comme MediaRecorder » : écrit par morceaux sur un tube, donc sans durée dans l'en-tête
    args = [FF, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1440x900:r=30:d=6"]
    if son:
        args += ["-f", "lavfi", "-i", "sine=f=440:d=6", "-c:a", "libopus"]
    args += ["-c:v", "libvpx", "-b:v", "1M", "-f", "webm", "-live", "1", "pipe:1"]
    octets = subprocess.run(args, capture_output=True).stdout
    (d / "scene.webm").write_bytes(octets)
    s = {"id": cid, "cree_utc": "2026-10-28T10:00:00+00:00", "debut_ms": 0, "fin_ms": 6000, "etat": "terminee",
         "duree_ms": 6000, "options": {"mode": "app"},
         "pistes": {"scene": {"mime": "video/webm", "ext": ".webm", "morceaux": 6, "octets": len(octets)}}}
    (d / "session.json").write_text(json.dumps(s), "utf-8")
    (d / f"{cid}.dzclics.json").write_text(json.dumps({"version": 1, "id": cid, "duree_ms": 6000,
        "cadre": {"largeur": 1440, "hauteur": 900, "mode": "app"},
        "evenements": [{"type": "ecran", "t": 0, "ecran": "quick"}, clic(1200, .3, .3),
                       {"type": "ecran", "t": 3000, "ecran": "studio"}]}), "utf-8")
    return d


cid = "c" * 16
fausse_capture(cid)
rx = M.remuxer(cid, "scene")
check("R1 remux : une durée lisible, le brut gardé", rx.name == "scene.remux.webm" and abs(sonde(rx)["d"] - 6) < 0.3
      and (M.racine() / cid / "scene.webm").is_file())
check("R2 sonder", M.sonder(rx)["largeur"] == 1440 and M.sonder(rx)["audio"] is True
      and abs(M.sonder(rx)["duree_ms"] - 6000) < 300)
base = M.valider(M.proposer(json.loads((M.racine() / cid / f"{cid}.dzclics.json").read_text("utf-8"))), 6000, cid)
G = M.graphe(base, M.segments(base, 6000), {"largeur": 1440, "hauteur": 900, "audio": True}, "16:9")
check("R3 graphe sans chemin, avec zoompan, crop, concat", "zoompan" in G and "crop=" in G and "concat=n=1" in G
      and ":\\" not in G and str(_tmp) not in G, G[:300])
sortie = _tmp / "outputs" / "captures"
r169 = M.rendre(cid, base, sortie)
s169 = sonde(r169["fichier"])
check("R4 16:9 -> 1920×1080, ≈ 6 s, son", (s169["l"], s169["h"]) == (1920, 1080) and abs(s169["d"] - 6) < 0.4
      and s169["a"], s169)
check("R5 chapitres en métadonnées et texte", len(s169["ch"]) == 2 and r169["texte"] == "00:00 Quick\n00:03 Studio"
      and r169["fichier"].name.startswith("montage_") and r169["fichier"].name.endswith(f"_{cid}_16x9.mp4"), r169)
r916 = M.rendre(cid, dict(base, format="9:16", coupes=[{"id": "c", "t0": 2000, "t1": 4000, "mode": "accelerer",
                                                       "vitesse": 8}]), sortie)
s916 = sonde(r916["fichier"])
check("R6 9:16 -> 1080×1920 ; 2 s accélérées ×8 -> ≈ 4,25 s", (s916["l"], s916["h"]) == (1080, 1920)
      and abs(s916["d"] - 4.25) < 0.35, s916)
r11 = M.rendre(cid, dict(base, format="1:1", coupes=[{"id": "c", "t0": 2000, "t1": 4000, "mode": "couper",
                                                     "vitesse": 8}]), sortie)
s11 = sonde(r11["fichier"])
check("R7 1:1 -> 1080×1080 ; 2 s coupées -> ≈ 4 s", (s11["l"], s11["h"]) == (1080, 1080) and abs(s11["d"] - 4) < 0.35, s11)


def pixel(p, t):
    raw = subprocess.run([FF, "-v", "error", "-ss", str(t), "-i", str(p), "-frames:v", "1", "-vf", "scale=64:36",
                          "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"], capture_output=True).stdout
    return raw
zoome = M.rendre(cid, dict(base, zooms=[{"id": "z", "t0": 0, "t1": 6000, "k": 2.5, "x": 0.2, "y": 0.2}]), sortie)
plat = M.rendre(cid, dict(base, zooms=[]), sortie)
check("R8 zoom visible (image zoomée ≠ image plate au même instant)", pixel(zoome["fichier"], 3) != pixel(plat["fichier"], 3)
      and len(pixel(plat["fichier"], 3)) == 64 * 36)
cid2 = "d" * 16
fausse_capture(cid2, son=False)
mm = M.valider(M.proposer({"duree_ms": 6000, "evenements": []}), 6000, cid2)
r2 = M.rendre(cid2, mm, sortie)
check("R9 source muette -> rendu avec une piste audio (silence)", sonde(r2["fichier"])["a"]
      and abs(sonde(r2["fichier"])["d"] - 6) < 0.4)
check("R10 montage écrit puis relu", (M.ecrire_montage(cid, base) or True) and M.lire_montage(cid) == base
      and M.lire_montage(cid2) is None)

(M.racine() / cid / "montage.json").write_text("{abîmé", "utf-8")
check("R11 montage.json abîmé -> None", M.lire_montage(cid) is None)
import threading                                                  # noqa: E402
(M.racine() / cid / "scene.remux.webm").unlink()
res = []
fils = [threading.Thread(target=lambda: res.append(M.remuxer(cid, "scene").name)) for _ in range(3)]
[f.start() for f in fils]; [f.join() for f in fils]
check("R12 trois remux simultanés : un seul fichier, aucun temporaire laissé", res == ["scene.remux.webm"] * 3
      and not list((M.racine() / cid).glob("*.tmp*")), (res, list((M.racine() / cid).iterdir())))
print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
