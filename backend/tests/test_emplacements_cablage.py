# -*- coding: utf-8 -*-
"""t379 (30/10/2026, lot « Réglages : chemins & apparence ») — le CÂBLAGE des emplacements de t378
(services/emplacements_cablage.py). Banc SERVEUR ; aucun réseau (faux sftp.exe : tests/_faux_sftp.py).
  [0] rien sans emplacement : un passage de la boucle n'écrit rien, ne crée aucun job ; la boucle est lancée ET
      arrêtée par le lifespan ;
  [S] sauvegarde vers un dossier : le paquet du transfert, renommé, SANS secret (.env, coffre), vérifiable
      (transfert.verifier) ; ROTATION à 7 sans toucher un dossier étranger ni un dossier sans manifeste ; échéance
      (jamais faite, > 24 h ; après un échec, pas avant 1 h) ; « Sauvegarder maintenant » ;
  [Z] sauvegarde SFTP : un .zip déposé dans le dossier distant, rotation des zips, rien laissé en local ;
  [M] miroir : rien tant qu'aucun emplacement « miroir » ; premier passage = repère posé, l'historique n'est pas
      recopié ; puis chaque rendu fini copié (nom-<id8>.ext), une seule fois, en file ; les jobs « emplacement »
      ignorés ; SFTP ; échec → job du Job Dock ;
  [J] Job Dock : un échec = UN job failed (provider emplacement, relance « emplacement ») même s'il dure ; « Réessayer »
      le rejoue (done) ; une réussite de la boucle clôt le job ; aucun coût compté ;
  [B] source de bibliothèque : index récursif des médias, SANS rien écrire là-bas ; dossier de sauvegardes écarté ;
      fichier servi confiné à l'index (« .. », absolu, hors index refusés) ; SFTP : index du dossier distant, fichier
      rapatrié dans un cache jetable exclu des sauvegardes ; « Importer » COPIE dans la Bibliothèque (source import,
      origine dans la recette) ; échéance de réindexation ;
  [R] routes : état, sauvegarder, index, indexer, fichier, importer, réessayer ; toutes locales (_local d'entrée) ;
  [E] chaque message d'erreur neuf est traduit (i18n_l10_erreurs.py --check).
Run (depuis backend/) : & $PY tests/test_emplacements_cablage.py"""
import ast, asyncio, json, os, pathlib, subprocess, sys, tempfile, time, uuid, zipfile
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcabl_"))
DONNEES = _tmp / "donnees"
os.environ["DEEPOTUS_DATA_DIR"] = str(DONNEES)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(DONNEES / 'deepotus.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(DONNEES / "assets" / "images")
os.environ["OUTPUTS_FOLDER"] = str(DONNEES / "assets" / "outputs")
SECRET_ENV = "sk-secret-du-banc-t379-ne-doit-pas-partir"
os.environ["FAL_KEY"] = SECRET_ENV
(DONNEES / "assets" / "images").mkdir(parents=True)
(DONNEES / "assets" / "outputs").mkdir(parents=True)
(DONNEES / ".env").write_text(f"FAL_KEY={SECRET_ENV}\n", encoding="utf-8")
(DONNEES / "coffre.dzk").write_bytes(b"DZKV1\nfaux-coffre")
(DONNEES / "assets" / "images" / "deja.png").write_bytes(b"\x89PNG faux")
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parents[1]
sys.path.insert(0, str(ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

SERVEUR = _tmp / "serveur"
(SERVEUR / "sauv").mkdir(parents=True)
JOURNAL = _tmp / "sftp.jsonl"
FAUX = _tmp / "faux_sftp.cmd"
FAUX.write_text(f'@"{sys.executable}" "{ICI / "_faux_sftp.py"}" %*\r\n', encoding="ascii")
os.environ.update({"DZ_SFTP_EXE": str(FAUX), "FAUX_SFTP_RACINE": str(SERVEUR), "FAUX_SFTP_JOURNAL": str(JOURNAL)})

from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import DATA_ROOT, settings                          # noqa: E402
from app.services import emplacements as E, emplacements_cablage as C, transfert as TR   # noqa: E402
from app.services.storage import init_db, async_session_factory, JobRecord, LibraryAsset   # noqa: E402
from sqlalchemy import select                                       # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


_BOUCLE = asyncio.new_event_loop()                                     # une seule boucle : aiosqlite garde ses connexions


def run(coro):
    return _BOUCLE.run_until_complete(coro)


async def jobs_emplacement():
    async with async_session_factory() as s:
        return (await s.execute(select(JobRecord).where(JobRecord.provider == "emplacement"))).scalars().all()


async def ajouter_job(statut="done", sortie=None, provider="seedance", quand=None):
    jid = str(uuid.uuid4())
    async with async_session_factory() as s:
        s.add(JobRecord(id=jid, status=statut, image_filename="x.png", provider=provider,
                        final_video_path=str(sortie) if sortie else None, completed_at=quand or datetime.utcnow()))
        await s.commit()
    return jid


def contenu_de(dossier: pathlib.Path) -> bytes:
    return b"".join(p.read_bytes() for p in sorted(dossier.rglob("*")) if p.is_file())


run(init_db())
c = TestClient(app)

# ══ [0] rien sans emplacement ══════════════════════════════════════════════════════════════════════════════════
print("[0] rien sans emplacement")
avant = sorted(p.name for p in DATA_ROOT.iterdir())
f0 = run(C.tic())
check("0.1 un passage sans emplacement ne fait rien", f0 == {"sauvegardes": [], "miroir": [], "index": []}, f0)
check("0.2 ... et n'écrit aucun fichier d'état ni d'index", sorted(p.name for p in DATA_ROOT.iterdir()) == avant,
      sorted(p.name for p in DATA_ROOT.iterdir()))
check("0.3 ... ni aucun job", run(jobs_emplacement()) == [])
MAIN = (ICI.parent / "app" / "main.py").read_text(encoding="utf-8")
check("0.4 la boucle est lancée par le lifespan ET arrêtée avec les autres", "asyncio.create_task(_EC.boucle())" in MAIN
      and "email_task, empl_task," in MAIN)

# ══ [S] sauvegarde vers un dossier ═════════════════════════════════════════════════════════════════════════════
print("[S] sauvegarde vers un dossier")
NAS = _tmp / "nas"
NAS.mkdir()
d = E.creer({"nom": "Disque", "type": "dossier", "chemin": str(NAS), "roles": ["sauvegarde"]})
check("S1 jamais faite : due", C.a_sauvegarder() == ["disque"])
T0 = time.mktime((2026, 10, 1, 3, 0, 0, 0, 0, -1))
r = C.sauvegarder("disque", quand=T0)
SV = NAS / C.DOSSIER_SAUVEGARDES
paquet = SV / "DeepotusVideo-Sauvegarde-2026-10-01-030000"
check("S2 le paquet est rangé et renommé", paquet.is_dir() and r["nom"] == paquet.name and (paquet / TR.MANIFESTE).is_file(),
      sorted(p.name for p in SV.iterdir()) if SV.exists() else "absent")
check("S3 la base part par instantané et la bibliothèque est copiée", (paquet / TR.DOSSIER_BASE / TR.NOM_BASE).is_file()
      and (paquet / TR.DOSSIER_DONNEES / "assets" / "images" / "deja.png").is_file())
check("S4 AUCUN secret : ni .env, ni coffre, ni la clé en clair", not list(paquet.rglob(".env"))
      and not list(paquet.rglob("coffre.dzk")) and SECRET_ENV.encode() not in contenu_de(paquet))
check("S5 la sauvegarde se vérifie (empreintes)", TR.verifier(paquet).get("ok") is True, TR.verifier(paquet))
check("S6 faite : plus due avant 24 h (ni tout de suite, ni 2 h ou 23 h plus tard)", C.a_sauvegarder() == []
      and C.a_sauvegarder(datetime.now() + timedelta(hours=2)) == []
      and C.a_sauvegarder(datetime.now() + timedelta(hours=23)) == [])
check("S7 due 25 h plus tard", C.a_sauvegarder(datetime.now() + timedelta(hours=25)) == ["disque"])
(SV / "Photos de vacances").mkdir()
(SV / "DeepotusVideo-Sauvegarde-2020-01-01-000000").mkdir()             # le nom, sans manifeste : pas à elle
for i in range(1, 10):
    C.sauvegarder("disque", quand=T0 + i * 86400)
siennes = sorted(p.name for p in SV.iterdir() if p.name.startswith(C.PREFIXE) and (p / TR.MANIFESTE).is_file())
check("S8 rotation : les 7 plus récentes restent", len(siennes) == 7 and siennes[0].endswith("2026-10-04-030000")
      and siennes[-1].endswith("2026-10-10-030000"), siennes)
check("S9 rotation : un dossier étranger et un dossier sans manifeste sont intacts",
      (SV / "Photos de vacances").is_dir() and (SV / "DeepotusVideo-Sauvegarde-2020-01-01-000000").is_dir())
E.modifier("disque", {"chemin": str(_tmp / "debranche")})
_e = C.lire_etat(); _e["sauvegardes"]["disque"] = {}; C._ecrire_etat(_e)    # aucune réussite récente : l'essai décide
try:
    C.sauvegarder("disque")
    check("S10 dossier débranché → EchecOperation introuvable", False)
except C.EchecOperation as ex:
    check("S10 dossier débranché → EchecOperation introuvable", ex.code == "introuvable", ex.code)
check("S11 après un échec : pas de nouvel essai avant 1 h, oui après", C.a_sauvegarder(datetime.now()) == [] and
      C.a_sauvegarder(datetime.now() + timedelta(minutes=61)) == ["disque"])
E.modifier("disque", {"chemin": str(NAS)})
_inst = TR.instantane_base


def _base_illisible(dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    raise __import__("sqlite3").OperationalError("unable to open database file")


TR.instantane_base = _base_illisible
try:
    C.sauvegarder("disque")
    check("S12 base illisible → EchecOperation (pas une exception brute)", False)
except C.EchecOperation as ex:
    check("S12 base illisible → EchecOperation (pas une exception brute)", ex.code == "echec"
          and "unable to open" in ex.detail, ex.detail)
finally:
    TR.instantane_base = _inst
check("S13 ... et aucun paquet à moitié écrit n'est laissé", not [p for p in SV.iterdir() if p.name.startswith(
    "DeepotusVideoGen-Transfert-")], sorted(p.name for p in SV.iterdir()))

# ══ [J] Job Dock ══════════════════════════════════════════════════════════════════════════════════════════════
print("[J] Job Dock")
E.modifier("disque", {"chemin": str(_tmp / "debranche")})
etat = C.lire_etat()
etat["sauvegardes"]["disque"] = {}
C._ecrire_etat(etat)
run(C.tic())
etat = C.lire_etat(); etat["sauvegardes"]["disque"] = {}; C._ecrire_etat(etat)
run(C.tic())                                                          # le NAS est toujours éteint
js = run(jobs_emplacement())
check("J1 un échec qui dure = UN seul job failed au Job Dock", len(js) == 1 and js[0].status == "failed"
      and "Sauvegarde → Disque" in (js[0].title or "") and js[0].error, [(j.status, j.title) for j in js])
_lj = c.get("/api/jobs?limit=50").json()
jl = [x for x in (_lj if isinstance(_lj, list) else _lj.get("jobs", []))
      if isinstance(x, dict) and x.get("job_id") == (js[0].id if js else "")]
check("J2 /api/jobs le montre avec la relance « emplacement »", jl and jl[0]["relance"] == "emplacement"
      and jl[0]["provider"] == "emplacement", jl)
r = c.post(f"/api/reglages/chemins/operations/{js[0].id}/reessayer")
check("J3 « Réessayer » tant que le NAS est éteint : reste failed", r.status_code == 200 and r.json()["status"] == "failed",
      r.text)
E.modifier("disque", {"chemin": str(NAS)})
r = c.post(f"/api/reglages/chemins/operations/{js[0].id}/reessayer")
check("J4 « Réessayer » une fois le NAS revenu : done", r.status_code == 200 and r.json()["status"] == "done", r.text)
check("J5 un job qui n'est pas en échec ne se réessaie pas (409) ; inconnu 404",
      c.post(f"/api/reglages/chemins/operations/{js[0].id}/reessayer").status_code == 409
      and c.post("/api/reglages/chemins/operations/zz/reessayer").status_code == 404)
jid_seed = run(ajouter_job(statut="failed"))
check("J6 un job ordinaire ne passe pas par cette route (404)",
      c.post(f"/api/reglages/chemins/operations/{jid_seed}/reessayer").status_code == 404)
E.modifier("disque", {"chemin": str(_tmp / "debranche")})
etat = C.lire_etat(); etat["sauvegardes"]["disque"] = {}; C._ecrire_etat(etat)
run(C.tic())
E.modifier("disque", {"chemin": str(NAS)})
etat = C.lire_etat(); etat["sauvegardes"]["disque"] = {}; C._ecrire_etat(etat)
run(C.tic())
check("J7 la boucle qui réussit ensuite CLÔT le job en échec", all(j.status == "done" for j in run(jobs_emplacement())),
      [(j.status, j.title) for j in run(jobs_emplacement())])
from app.config import settings as _cfg                                # la langue de l'interface (UI_LANG)
_cfg.UI_LANG = "en"
_e = C.lire_etat(); _e["sauvegardes"]["disque"] = {}; C._ecrire_etat(_e)
E.modifier("disque", {"chemin": str(_tmp / "debranche")})
run(C.tic())
_en = [j for j in run(jobs_emplacement()) if j.status == "failed"]
check("J7b interface en anglais : titre et erreur du job dans la langue de l'interface", _en
      and _en[0].title == "Backup → Disque" and _en[0].error == "folder not found or unreachable",
      [(j.title, j.error) for j in _en])
_cfg.UI_LANG = "fr"
E.modifier("disque", {"chemin": str(NAS)})
_e = C.lire_etat(); _e["sauvegardes"]["disque"] = {}; C._ecrire_etat(_e)
run(C.tic())
check("J7c chaque code d'état a son texte FR/EN au Dock (messages.json)", all(
    C._dit(f"emplacements.etat.{k}", "fr") != f"emplacements.etat.{k}" and C._dit(f"emplacements.etat.{k}", "en")
    != C._dit(f"emplacements.etat.{k}", "fr") or k == "joignable" and C._dit("emplacements.etat.joignable", "en") == "reachable"
    for k in E.ETATS))
usage = c.get("/api/cost/usage").json()
check("J8 aucun coût compté pour ces jobs (pas de « non-tarifé:emplacement »)",
      "non-tarifé:emplacement" not in json.dumps(usage, ensure_ascii=False), str(usage)[:300])

# ══ [Z] sauvegarde SFTP ═══════════════════════════════════════════════════════════════════════════════════════
print("[Z] sauvegarde SFTP")
z = E.creer({"nom": "Serveur", "type": "sftp", "hote": "nas.local", "utilisateur": "olivia", "dossier_distant": "/sauv",
             "roles": ["sauvegarde"]})
tmp_avant = set(pathlib.Path(tempfile.gettempdir()).glob("dzsauvegarde_*"))
for i in range(9):
    C.sauvegarder("serveur", quand=T0 + i * 86400)
zips = sorted(p.name for p in (SERVEUR / "sauv" / C.DOSSIER_SAUVEGARDES).iterdir())
check("Z1 un .zip par sauvegarde, rotation à 7", len(zips) == 7 and all(n.endswith(".zip") for n in zips)
      and zips[0] == "DeepotusVideo-Sauvegarde-2026-10-03-030000.zip", zips)
with zipfile.ZipFile(SERVEUR / "sauv" / C.DOSSIER_SAUVEGARDES / zips[-1]) as zz:
    noms = zz.namelist()
    tout = b"".join(zz.read(n) for n in noms)
check("Z2 le zip contient manifeste, base et bibliothèque, aucun secret", TR.MANIFESTE in noms
      and f"{TR.DOSSIER_BASE}/{TR.NOM_BASE}" in noms and not any(n.endswith(".env") or "coffre" in n for n in noms)
      and SECRET_ENV.encode() not in tout, noms[:6])
check("Z3 rien n'est laissé dans le dossier temporaire", set(pathlib.Path(tempfile.gettempdir()).glob("dzsauvegarde_*"))
      == tmp_avant)
E.supprimer("serveur")

# ══ [M] miroir des rendus ═════════════════════════════════════════════════════════════════════════════════════
print("[M] miroir")
REND = DONNEES / "assets" / "outputs" / "final"
REND.mkdir(parents=True, exist_ok=True)
v1 = REND / "rendu_un.mp4"; v1.write_bytes(b"video-un" * 100)
jv_avant = run(ajouter_job(sortie=v1, quand=datetime.utcnow() - timedelta(minutes=5)))
check("M0 sans emplacement « miroir » : rien, aucun repère", run(C.balayer_miroir()) == []
      and not C.lire_etat().get("miroir_depuis"))
MIR = _tmp / "miroir"; MIR.mkdir()
E.creer({"nom": "Miroir", "type": "dossier", "chemin": str(MIR), "roles": ["miroir"]})
check("M1 premier passage : repère posé, l'historique n'est pas recopié", run(C.balayer_miroir()) == []
      and C.lire_etat().get("miroir_depuis") and not (MIR / C.DOSSIER_RENDUS).exists())
time.sleep(1.1)
v2 = REND / "rendu_deux.mp4"; v2.write_bytes(b"video-deux" * 100)
jv2 = run(ajouter_job(sortie=v2))
run(ajouter_job(sortie=v2, provider="emplacement"))                   # un job né d'une opération : jamais recopié
run(ajouter_job(statut="failed", sortie=v2))                          # un échec de rendu : rien à copier
f = run(C.balayer_miroir())
cible = MIR / C.DOSSIER_RENDUS / f"rendu_deux-{jv2[:8]}.mp4"
check("M2 le rendu fini est copié, nommé nom-<id8>.ext, octet pour octet", cible.is_file()
      and cible.read_bytes() == v2.read_bytes() and len(f) == 1, f)
check("M3 seuls les rendus finis d'après le repère (ni l'historique, ni les jobs emplacement, ni les échecs)",
      sorted(p.name for p in (MIR / C.DOSSIER_RENDUS).iterdir()) == [cible.name])
check("M4 un second passage ne recopie rien", run(C.balayer_miroir()) == [])
check("M5 aucun .part laissé", not list((MIR / C.DOSSIER_RENDUS).glob("*.part")))
E.creer({"nom": "Miroir distant", "type": "sftp", "hote": "nas.local", "utilisateur": "olivia",
         "dossier_distant": "/sauv", "roles": ["miroir"]})
time.sleep(1.1)
v3 = REND / "rendu_trois.mp4"; v3.write_bytes(b"video-trois" * 100)
jv3 = run(ajouter_job(sortie=v3))
E.modifier("miroir", {"chemin": str(_tmp / "debranche")})
f = run(C.balayer_miroir())
distant = SERVEUR / "sauv" / C.DOSSIER_RENDUS / f"rendu_trois-{jv3[:8]}.mp4"
check("M6 SFTP : déposé dans <dossier distant>/DeepotusVideo-Rendus", distant.is_file()
      and distant.read_bytes() == v3.read_bytes(), f)
ech = [j for j in run(jobs_emplacement()) if j.status == "failed" and "Miroir → Miroir" in (j.title or "")]
check("M7 un miroir en échec = un job failed au Job Dock (titre avec le fichier)", len(ech) == 1
      and "rendu_trois.mp4" in ech[0].title, [(j.status, j.title) for j in run(jobs_emplacement())])
check("M8 le repère avance quand même : la file ne bloque pas sur un échec", run(C.balayer_miroir()) == [])
E.modifier("miroir", {"chemin": str(MIR)})
r = c.post(f"/api/reglages/chemins/operations/{ech[0].id}/reessayer")
check("M9 « Réessayer » le miroir : copié", r.json().get("status") == "done"
      and (MIR / C.DOSSIER_RENDUS / f"rendu_trois-{jv3[:8]}.mp4").is_file(), r.text)
E.supprimer("miroirdistant")

# ══ [B] source de bibliothèque ════════════════════════════════════════════════════════════════════════════════
print("[B] source de bibliothèque")
SRC = _tmp / "photos"
(SRC / "2025" / "ete").mkdir(parents=True)
(SRC / ".cache").mkdir()
(SRC / C.DOSSIER_SAUVEGARDES).mkdir()
(SRC / "plage.jpg").write_bytes(b"\xff\xd8 jpeg plage")
(SRC / "2025" / "ete" / "vague.png").write_bytes(b"\x89PNG vague")
(SRC / "2025" / "clip.mp4").write_bytes(b"mp4")
(SRC / "2025" / "voix.wav").write_bytes(b"RIFF")
(SRC / "notes.txt").write_text("pas un média", encoding="utf-8")
(SRC / ".cache" / "cache.png").write_bytes(b"x")
(SRC / C.DOSSIER_SAUVEGARDES / "base.png").write_bytes(b"x")
etat_src = {str(p): (p.stat().st_mtime, p.stat().st_size) for p in SRC.rglob("*")}
E.creer({"nom": "Photos", "type": "dossier", "chemin": str(SRC), "roles": ["bibliotheque"]})
check("B0 jamais indexée : due", "photos" in C.a_indexer())
idx = C.indexer("photos")
chemins = sorted(x["chemin"] for x in idx["fichiers"])
check("B1 index récursif des médias (images, vidéos, sons), cachés et sauvegardes écartés",
      chemins == ["2025/clip.mp4", "2025/ete/vague.png", "2025/voix.wav", "plage.jpg"], chemins)
check("B2 chaque entrée a son genre et sa taille", {x["chemin"]: x["genre"] for x in idx["fichiers"]}["2025/clip.mp4"]
      == "video" and all(x["octets"] > 0 for x in idx["fichiers"]))
check("B3 l'index est gardé hors de l'emplacement et relu", C.lire_index("photos")["fichiers"] == idx["fichiers"]
      and (DATA_ROOT / "emplacements_index" / "photos.json").is_file())
check("B4 plus due juste après, due 7 h plus tard", "photos" not in C.a_indexer()
      and "photos" in C.a_indexer(datetime.now() + timedelta(hours=7)))
r = c.get("/api/reglages/chemins/photos/fichier", params={"chemin": "2025/ete/vague.png"})
check("B5 un fichier indexé se lit", r.status_code == 200 and r.content == b"\x89PNG vague", r.status_code)
for mauvais in ("../nas/x.png", "notes.txt", str(SRC / "plage.jpg"), "2025/../plage.jpg", ".cache/cache.png"):
    r = c.get("/api/reglages/chemins/photos/fichier", params={"chemin": mauvais})
    check(f"B6 refusé : {mauvais!r}", r.status_code == 400, r.status_code)
check("B7 une source qui n'est pas « bibliothèque » ne sert rien",
      c.get("/api/reglages/chemins/disque/fichier", params={"chemin": "x.png"}).status_code == 400)
E.modifier("photos", {"roles": ["sauvegarde"]})
check("B7b un fichier DÉJÀ indexé ne se lit plus quand le rôle « bibliothèque » est retiré",
      c.get("/api/reglages/chemins/photos/fichier", params={"chemin": "plage.jpg"}).status_code == 400)
E.modifier("photos", {"roles": ["bibliotheque"]})
r = c.post("/api/reglages/chemins/photos/importer", json={"chemin": "plage.jpg"})
imp = r.json() if r.status_code == 200 else {}
dest = settings.images_path / imp.get("filename", "?")
check("B8 « Importer » COPIE l'image dans la Bibliothèque", r.status_code == 200 and dest.is_file()
      and dest.read_bytes() == (SRC / "plage.jpg").read_bytes(), r.text)


async def _asset(nom):
    async with async_session_factory() as s:
        return await s.get(LibraryAsset, nom)
a = run(_asset(imp.get("filename", "?")))
check("B9 indexée en Bibliothèque : source import, origine dans la recette", a is not None and a.source == "import"
      and "photos" in (a.recette or ""), a and (a.source, a.recette))
check("B10 une vidéo ne s'importe pas (images et sons seulement)",
      c.post("/api/reglages/chemins/photos/importer", json={"chemin": "2025/clip.mp4"}).status_code == 400)
check("B11 la source n'a JAMAIS été modifiée (aucun fichier ajouté ni touché)",
      {str(p): (p.stat().st_mtime, p.stat().st_size) for p in SRC.rglob("*")} == etat_src)
(SERVEUR / "sauv" / "affiche.png").write_bytes(b"\x89PNG affiche")
(SERVEUR / "sauv" / "lisez.txt").write_text("x", encoding="utf-8")
E.creer({"nom": "NAS photos", "type": "sftp", "hote": "nas.local", "utilisateur": "olivia", "dossier_distant": "/sauv",
         "roles": ["bibliotheque"]})
idx = C.indexer("nasphotos")
check("B12 SFTP : index du dossier distant (médias seulement, taille lue par ls -ln)",
      [(x["chemin"], x["octets"]) for x in idx["fichiers"]] == [("affiche.png", len(b"\x89PNG affiche"))], idx["fichiers"])
r = c.get("/api/reglages/chemins/nasphotos/fichier", params={"chemin": "affiche.png"})
caches = list((settings.outputs_path / "_cache" / "emplacements" / "nasphotos").glob("*.png"))
check("B13 SFTP : le fichier est rapatrié dans un cache jetable puis servi", r.status_code == 200
      and r.content == b"\x89PNG affiche" and len(caches) == 1, r.status_code)
check("B14 ce cache est exclu des sauvegardes (jetable du transfert)",
      TR.exclu(caches[0].relative_to(DATA_ROOT).as_posix(), None)[0] if caches else False)
E.modifier("nasphotos", {"dossier_distant": "/absent"})
C._ecrire_etat(C.lire_etat())
idx_av = C.lire_index("nasphotos")
_vieux = dict(idx_av, quand="2020-01-01T00:00:00")                    # échéance de réindexation dépassée
(DATA_ROOT / "emplacements_index" / "nasphotos.json").write_text(json.dumps(_vieux), encoding="utf-8")
f = run(C.tic())
check("B15 index en échec : l'ancien index reste, daté, avec son erreur ; un job au Dock",
      C.lire_index("nasphotos")["fichiers"] == idx_av["fichiers"] and C.lire_index("nasphotos").get("erreur")
      and any("Index → NAS photos" in (j.title or "") and j.status == "failed" for j in run(jobs_emplacement())))
check("B16 ... et pas un nouvel essai à chaque passage", "nasphotos" not in C.a_indexer())

# ══ [R] routes ═══════════════════════════════════════════════════════════════════════════════════════════════
print("[R] routes")
j = c.get("/api/reglages/chemins/etat").json()
check("R1 état : dernière sauvegarde et index par emplacement", j["emplacements"]["disque"]["sauvegarde"]["ok"] is True
      and j["emplacements"]["photos"]["index"]["fichiers"] == 4 and j["garder"] == 7, j)
r = c.post("/api/reglages/chemins/disque/sauvegarder")
check("R2 « Sauvegarder maintenant »", r.status_code == 200 and r.json()["ok"] and r.json()["nom"].startswith(C.PREFIXE),
      r.text)
E.modifier("disque", {"chemin": str(_tmp / "debranche")})
r = c.post("/api/reglages/chemins/disque/sauvegarder")
check("R3 ... en échec : rendu avec son code, pas levé", r.status_code == 200 and r.json() == {
    **r.json(), "ok": False, "code": "introuvable"}, r.text)
E.modifier("disque", {"chemin": str(NAS)})
r = c.post("/api/reglages/chemins/photos/indexer")
check("R4 « Indexer »", r.status_code == 200 and r.json()["ok"] and len(r.json()["fichiers"]) == 4, r.text[:200])
check("R5 index d'un inconnu → 404", c.get("/api/reglages/chemins/zz/index").status_code == 404)
_sr = ast.parse((ICI.parent / "app" / "api" / "settings_routes.py").read_text(encoding="utf-8"))
_ch = [fn for fn in _sr.body if isinstance(fn, ast.AsyncFunctionDef) and any(
    isinstance(dd, ast.Call) and dd.args and isinstance(dd.args[0], ast.Constant)
    and str(dd.args[0].value).startswith("/chemins") for dd in fn.decorator_list)]
_sans = [fn.name for fn in _ch if not any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "_local"
                                          for st in fn.body[:4] for n in ast.walk(st))]
check(f"R6 les {len(_ch)} routes /chemins appellent _local d'entrée", len(_ch) >= 14 and not _sans, _sans)
cd = TestClient(app, client=("192.168.1.50", 5000))
check("R7 un autre appareil ne lit aucun fichier d'une source",
      cd.get("/api/reglages/chemins/photos/fichier", params={"chemin": "plage.jpg"}).status_code in (401, 403))

# ══ [E] traductions L10 ═══════════════════════════════════════════════════════════════════════════════════════
print("[E] traductions L10")
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l10_erreurs.py"), "--check"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", cwd=str(RACINE),
                   env=dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8"))
check("E1 i18n_l10_erreurs.py --check", r.returncode == 0, (r.stdout + r.stderr)[-600:])

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
