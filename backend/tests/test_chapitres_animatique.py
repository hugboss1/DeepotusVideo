# -*- coding: utf-8 -*-
"""Plan chapitres T10 (tache #63 du suivi, 02/10/2026) — l'ANIMATIQUE : les plans du storyboard montes en video de
repetition (540×960, 30 i/s) avant tout rendu video payant.
  - `plan()` PUR : l'image de production prime sur le croquis, sinon un carton ; la voix temoin FIXE la duree ;
    les durees sont recalees en images entieres ;
  - le SON, corrige du plan (mesure au ffmpeg reel) : clips muets + UNE piste construite (voix ou silence exact par
    plan) — un plan muet en tete ou au milieu ne perd ni ne decale plus rien ;
  - DECISIONS DE L'UTILISATEUR (02/10) : muette par DEFAUT ; voix ElevenLabs sur demande, garde des plafonds, voix
    en CACHE (un re-rendu ne repaie rien), voix du NARRATEUR de la bible ; le GET donne le devis et ne cree rien.
ffmpeg REEL (petite definition, quelques secondes), voix SIMULEE (un son sinus), data-dir isole, cles videes.
Temoin positif : la base (f96f864c) n'a ni le service ni la route.
Run (depuis backend/) : & $PY tests/test_chapitres_animatique.py"""
import json, os, pathlib, sqlite3, subprocess, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzanim_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OLLAMA_URL", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "FAL_KEY"):
    os.environ[k] = ""
os.environ["ELEVENLABS_API_KEY"] = "cle-de-banc"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "f96f864c"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/animatique_service.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni le service ni la route d'animatique", r0.returncode != 0 and r1.returncode == 0
      and b'"/chapters/{chapter_id}/animatique"' not in r1.stdout)


def sonde(f, *a):
    return subprocess.run(["ffprobe", "-v", "error", *a, str(f)], capture_output=True, text=True).stdout.strip()


def flux(f):
    """{type: duree} des flux d'un fichier."""
    out = {}
    for l in sonde(f, "-show_entries", "stream=codec_type,duration", "-of", "csv=p=0").splitlines():
        t, _, dd = l.partition(",")
        try:
            out[t] = float(dd)
        except ValueError:
            out[t] = None
    return out


def silences(f):
    sd = subprocess.run(["ffmpeg", "-i", str(f), "-af", "silencedetect=n=-40dB:d=0.3", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    return [float(l.split(": ")[1].split(" ")[0]) for l in sd.splitlines() if "silence_start" in l or "silence_end" in l]


def ton(dest, duree):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={duree}", "-ac", "1", "-ar", "22050",
                    str(dest)], capture_output=True, check=True)
    return dest


try:
    from app.services import animatique_service as AN               # noqa: E402
except ImportError as e:
    AN = None
    check("T2 le service existe", False, str(e))

if AN:
    print("[P] le plan de montage (pur)")
    sh = [{"id": "a", "idx": 0, "image": "prod.png", "sketch_image": "croquis.png", "action": "Vane entre", "duration_s": 7.0},
          {"id": "b", "idx": 1, "sketch_image": "croquis.png", "source_text": "La pluie", "duration_s": 2.0},
          {"id": "c", "idx": 2, "action": "", "duration_s": None}]
    e = AN.plan(sh, voix={"a": 1.234, "b": 0.3})
    check("P1 l'image de PRODUCTION prime sur le croquis ; sans image : un carton", [x["image"] for x in e] == ["prod.png", "croquis.png", None]
          and [x["carton"] for x in e] == [False, False, True], str(e))
    check("P2 la voix FIXE la duree (1,234 s -> 37 images = 1,233 s) ; trop courte (0,3 s), c'est la duree du plan qui vaut",
          (e[0]["dur"], e[0]["source_duree"]) == (1.233, "voix") and (e[1]["dur"], e[1]["source_duree"]) == (2.0, "plan"), str(e))
    check("P3 sans duree reglee : 4 s ; le texte du plan vient de l'action, sinon du texte source",
          e[2]["dur"] == 4.0 and e[0]["texte"] == "Vane entre" and e[1]["texte"] == "La pluie")
    check("P4 la cle de cache : stable, et differente si la VOIX ou la LANGUE change",
          AN.cle_voix("x", "v1", "fr") == AN.cle_voix("x", "v1", "fr") != AN.cle_voix("x", "v2", "fr") != AN.cle_voix("x", "v1", "en"))
    try:
        AN.dossier(_tmp, "../evade"); refus = False
    except ValueError:
        refus = True
    check("P5 un identifiant douteux est REFUSE ; sans `creer`, rien n'est cree", refus and not AN.dossier(_tmp, "abc").exists())
    fichiers, filtre = AN.filtre_audio([{"shot_id": "a", "dur": 1.0}, {"shot_id": "b", "dur": 2.0}], {"b": ton(_tmp / "t.mp3", 0.5)})
    check("P6 la piste : un silence EXACT pour le muet, la voix completee puis coupee a la duree du clip",
          fichiers == [_tmp / "t.mp3"] and "anullsrc=r=44100:cl=stereo,atrim=0:1.0" in filtre and "[1:a]aresample=44100" in filtre
          and "apad,atrim=0:2.0" in filtre and filtre.endswith("[a0][a1]concat=n=2:v=0:a=1[a]"), filtre)

    print("\n[S] le son, au ffmpeg reel")
    o = _tmp / "s"
    e = AN.plan([{"id": "a", "idx": 0, "action": "muet", "duration_s": 1.0}, {"id": "b", "idx": 1, "action": "voix", "duration_s": 9},
                 {"id": "c", "idx": 2, "action": "muet", "duration_s": 1.0}], voix={"b": 1.2})
    f = AN.rendre(e, images=_tmp / "images", sortie=o, audios={"b": ton(_tmp / "v.mp3", 1.2)})
    fl = flux(f)
    check("S1 un plan MUET EN TETE ne perd plus la piste : video ET audio, 3,2 s chacune, 540×960",
          set(fl) == {"video", "audio"} and abs((fl["video"] or 0) - 3.2) < 0.05 and abs((fl["audio"] or 0) - 3.2) < 0.05
          and sonde(f, "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0") == "540,960", str(fl))
    s = silences(f)
    check("S2 la voix est A SA PLACE : silence jusqu'a 1,0 s, voix jusqu'a 2,2 s, puis silence (aucun decalage)",
          len(s) >= 3 and abs(s[1] - 1.0) < 0.06 and abs(s[2] - 2.2) < 0.06, str(s))
    check("S3 les clips par plan sont GARDES et MUETS (le son ne vit que sur la piste unique), la video muette intermediaire non",
          sorted(p.name for p in o.glob("p*.mp4")) == ["p000.mp4", "p001.mp4", "p002.mp4"] and not (o / "animatique_muet.mp4").exists()
          and all(set(flux(p)) == {"video"} for p in o.glob("p*.mp4")), str([flux(p) for p in o.glob("p*.mp4")]))
    f2 = AN.rendre(e[:2], images=_tmp / "images", sortie=o)
    check("S4 sans voix : pas de piste ; et un rendu plus COURT purge les clips du precedent",
          set(flux(f2)) == {"video"} and sorted(p.name for p in o.glob("p*.mp4")) == ["p000.mp4", "p001.mp4"], str(flux(f2)))

# ── les routes ────────────────────────────────────────────────────────────────────────────────────────────────────
_stub = types.ModuleType("fal_client")
sys.modules["fal_client"] = _stub
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import app.api.routes as RT                                         # noqa: E402
from app.services import voice_providers as VP                      # noqa: E402
from app.services import elevenlabs_service as ELS                  # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
VP.resolve_provider = lambda requested=None: "elevenlabs"
VP.voicebox_reachable = lambda: False
APPELS_TTS = []


def _faux_tts(self, text, output_path, language="EN", voice_id=None, **kw):
    APPELS_TTS.append({"text": text, "voice_id": voice_id, "language": language})
    ton(pathlib.Path(output_path), 1.0)
    return pathlib.Path(output_path)
ELS.VoiceoverService.generate_long = _faux_tts
ELS.VoiceoverService.is_enabled = staticmethod(lambda: True)


def js(r):
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def depenses():
    try:
        return sqlite3.connect(str(_DB)).execute("SELECT count(*) FROM depenses").fetchone()[0]
    except sqlite3.OperationalError:
        return -1


def job(c, r):
    j = js(r)
    return js(c.get(f"/api/atelier/manuscript/{j.get('job_id')}")) if j.get("job_id") else {}


print("\n[A] les routes")
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as c:
    check("A1 chapitre inconnu : 404", c.get("/api/chapters/inconnu/animatique").status_code == 404)
    check("A2 identifiant douteux : 400", c.get("/api/chapters/a.b/animatique").status_code == 400)
    vide = js(c.post("/api/chapters", json={"title": "Vide", "script_text": ""}))
    check("A3 sans storyboard : 400", c.post(f"/api/chapters/{vide.get('id')}/animatique", json={}).status_code == 400)
    ch = js(c.post("/api/chapters", json={"title": "C", "script_text": "Vane entre sous la pluie.\n\nYsolde se tait.\n\nLa porte claque."}))
    cid = ch.get("id")
    shots = js(c.post(f"/api/chapters/{cid}/storyboard/decoupe", json={"method": "paragraph"})).get("shots", [])
    for s, dur in zip(shots, (1.0, 1.5, 1.0)):
        c.put(f"/api/shots/{s['id']}", json={"duration_s": dur})
    r = c.get(f"/api/chapters/{cid}/animatique")
    g = js(r)
    dossier = _tmp / "outputs" / "animatique" / str(cid)
    textes = "Vane entre sous la pluie." + "Ysolde se tait." + "La porte claque."
    check("A4 le GET d'un chapitre jamais rendu : rien n'existe, et RIEN n'est cree sur le disque",
          r.status_code == 200 and g.get("existe") is False and g.get("storyboard") == 3 and not dossier.exists(), f"{r.status_code} {r.text[:200]}")
    from app.services import pricing as PR
    v = g.get("voix") or {}
    check("A5 le DEVIS de la voix : ElevenLabs, 3 voix a generer, leurs caracteres, et le cout a ce tarif",
          v.get("fournisseur") == "elevenlabs" and v.get("a_generer") == 3 and v.get("caracteres") == len(textes)
          and v.get("usd") == round(len(textes) * PR.elevenlabs_rate(), 4), str(v))
    n_dep = depenses()
    r = c.post(f"/api/chapters/{cid}/animatique", json={})
    st = job(c, r)
    g = js(c.get(f"/api/chapters/{cid}/animatique"))
    check("A6 PAR DEFAUT, MUETTE : aucune voix, aucune depense ; le job finit « terminé », 3 plans, 3,5 s",
          r.status_code == 200 and js(r).get("voix") is False and APPELS_TTS == [] and depenses() == n_dep
          and st.get("phase") == "terminé" and st.get("stats", {}).get("duree_s") == 3.5 and g.get("existe") and g.get("plans") == 3,
          f"{r.status_code} {st}")
    m = c.get(f"/api/chapters/{cid}/animatique.mp4")
    check("A7 le fichier est servi (video/mp4)", m.status_code == 200 and m.headers.get("content-type") == "video/mp4" and len(m.content) > 1000)
    r = c.post(f"/api/chapters/{cid}/animatique", json={"voix": True})
    check("A8 voix demandee SANS Narrateur dans la bible : 400 parlant, aucun appel", r.status_code == 400 and "Narrateur" in r.text and APPELS_TTS == [])
    narr = js(c.post("/api/bible/entities", json={"kind": "character", "name": "Narrateur", "description": "voix"}))
    sqlite3.connect(str(_DB)).execute("UPDATE bible_entities SET voice_id='voix-narr' WHERE id=?", (narr.get("id"),)).connection.commit()
    r = c.post(f"/api/chapters/{cid}/animatique", json={"voix": True})
    st = job(c, r)
    dep = sqlite3.connect(str(_DB)).execute("SELECT moteur, categorie FROM depenses").fetchall()
    check("A9 avec le Narrateur : 3 voix, SA voix, en francais ; la depense est ecrite (elevenlabs, chapitres)",
          st.get("phase") == "terminé" and len(APPELS_TTS) == 3 and {a["voice_id"] for a in APPELS_TTS} == {"voix-narr"}
          and {a["language"] for a in APPELS_TTS} == {"FR"} and ("elevenlabs", "chapitres") in dep, f"{st} {APPELS_TTS} {dep}")
    f = dossier / "animatique.mp4"
    check("A10 la voix FIXE la duree : 3 plans d'1 s -> 3,0 s, avec une piste son", st.get("stats", {}).get("duree_s") == 3.0
          and set(flux(f)) == {"video", "audio"}, f"{st.get('stats')} {flux(f)}")
    n_dep, n_tts = depenses(), len(APPELS_TTS)
    v = js(c.get(f"/api/chapters/{cid}/animatique")).get("voix") or {}
    r = c.post(f"/api/chapters/{cid}/animatique", json={"voix": True})
    st = job(c, r)
    check("A11 le CACHE : devis a 0, et un re-rendu avec voix ne repaie rien (aucun appel, aucune depense)",
          v.get("a_generer") == 0 and v.get("usd") == 0 and len(APPELS_TTS) == n_tts and depenses() == n_dep and st.get("phase") == "terminé",
          f"{v} {len(APPELS_TTS)}/{n_tts} {depenses()}/{n_dep}")
    from app.services import plafonds as PL
    PL.enregistrer({"global_usd": 0.0001, "par_moteur": {}, "alerte_pct": 80})
    c.put(f"/api/shots/{shots[2]['id']}", json={"action": "Un texte neuf, donc une voix a payer."})
    r = c.post(f"/api/chapters/{cid}/animatique", json={"voix": True})
    check("A12 une voix neuve au-dela du plafond : 402 dz_plafond, AUCUN appel", r.status_code == 402 and "dz_plafond" in r.text
          and len(APPELS_TTS) == n_tts, f"{r.status_code} {r.text[:160]}")
    r = c.post(f"/api/chapters/{cid}/animatique", json={"voix": True}, headers={"X-DZ-Plafond": "confirme"})
    st = job(c, r)
    check("A13 confirme : seule la voix NEUVE part (une, pas trois)", st.get("phase") == "terminé" and len(APPELS_TTS) == n_tts + 1
          and APPELS_TTS[-1]["text"].startswith("Un texte neuf"), f"{st} {APPELS_TTS[-1:]}")
    PL.enregistrer({"global_usd": 0, "par_moteur": {}, "alerte_pct": 80})
    src = (_ICI / "test_plafonds_garde.py").read_text(encoding="utf-8")
    check("A14 recensee parmi les routes PAYANTES", '("routes", "POST", "/chapters/{chapter_id}/animatique")' in src)
    RT._MS_JOBS.clear()
    for i in range(30):
        RT._ms_register(f"j{i}", {"phase": "terminé"})
    RT._ms_register("neuf", {"phase": "animatique"})
    check("A15 les jobs « terminé » sont evinces comme les « done » (20 gardes)", len(RT._MS_JOBS) <= 22, str(len(RT._MS_JOBS)))

print("\n[U] /atelier (cablage ; comportement prouve dans le navigateur)")
import re as _re                                                     # noqa: E402
_at = _ICI.parent.parent / "frontend" / "atelier"
_js = (_at / "atelier.js").read_text(encoding="utf-8")
_html = (_at / "index.html").read_text(encoding="utf-8")
_fn = _js.split("async function monterAnimatique(")[1].split("\n}\n")[0] if "async function monterAnimatique(" in _js else ""
# la modale de l'animatique SEULE : jusqu'au bloc de premier niveau suivant (une autre modale peut la suivre, #66)
_modale = _re.split(r"\n<div id=", _html.split('<div id="animModal"')[1])[0] if '<div id="animModal"' in _html else ""
_boutons = _re.findall(r"<button[^>]*>", '<button id="animBtn"' + _html.split('<button id="animBtn"')[1].split(">")[0] + ">" + _modale) if _modale else []
check("U1 le bouton 🎞 et ceux de la modale ont TOUS un title", len(_boutons) == 3 and all("title=" in b for b in _boutons), str(_boutons))
check("U2 la case « voix témoin » n'est PAS cochee d'origine : muette par defaut", 'id="animVoix"' in _modale
      and not _re.search(r'id="animVoix"[^>]*checked', _modale) and '{ voix, language: "fr" }' in _fn)
_garde = _fn.find('if (v.fournisseur === "elevenlabs" && v.a_generer > 0 && !await window.__dzDialogue.confirmer(')
_retour = _fn.find(")) return;", _garde) if _garde >= 0 else -1
_post = _fn.find('api.send("POST"')
check("U3 le cout des voix NON en cache est CONFIRME avant le POST (dialogue maison)", 0 <= _garde < _retour < _post,
      f"garde={_garde} retour={_retour} post={_post}")
check("U4 sa propre progression (pas la barre de l'agent manuscrit), aucun dialogue natif",
      "animProgres(st)" in _fn and "msSetProgress" not in _fn and "#msModal" not in _fn and not _re.search(r"(?<![.\w])confirm\(", _fn))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
