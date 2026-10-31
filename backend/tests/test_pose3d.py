# -*- coding: utf-8 -*-
"""t376 (29/10/2026) — 3D : choix Aucune / T-pose / A-pose (pose3d + asset3d_service + routes).

Ce que le banc prouve :
  A. détection « personnage » par le sujet tapé (D6) : mots entiers FR/EN, personnage > doute > objet, vide = doute ;
  B. normalisation de la pose (pose prime, ancien booléen tpose, valeur inconnue refusée) ;
  C. état du choix par moteur (moteur / vues / grisé) et par sujet, raison et avertissement ;
  D. transmission aux moteurs : phrase de pose sur TOUTES les vues, aucune sans pose, ancien comportement gardé
     sans pose ; Rodin TAPose + prompt ; les moteurs sans paramètre ne reçoivent rien ;
  E. routes : refus 400 AVANT toute dépense (moteur, sujet objet, vues manquantes), pose transmise au moteur
     de bout en bout (fal factice), état et devis gratuits ;
  F. classification vision : 409 sans accord, rien d'envoyé ; une fois par image (cache par empreinte) ; coût hors
     accord refusé avant l'envoi ; tirer_garde (plafond « moteurs3d ») ; la vision « personnage » réactive le choix.
Run : & $PY tests/test_pose3d.py   (depuis backend/)
"""
import asyncio, json, os, pathlib, sys, tempfile, types
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzpose3d_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["FAL_KEY"] = "test-key"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir()
(_tmp / "outputs").mkdir()
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

CALLS = []


async def _fake_subscribe(model, arguments=None, **kw):
    CALLS.append({"model": model, "arguments": arguments})
    if "seedream" in str(model):
        return {"images": [{"url": "http://fal.test/vue.png"}]}
    return {"model_mesh": {"url": "http://fal.test/model.glb"}}


async def _fake_upload(path):
    CALLS.append({"model": "upload", "arguments": str(path)})
    return "http://fal.test/up.png"


_stub = types.ModuleType("fal_client")
_stub.subscribe_async = _fake_subscribe
_stub.upload_file_async = _fake_upload
sys.modules["fal_client"] = _stub

from PIL import Image                                               # noqa: E402
from app.config import settings                                     # noqa: E402
from app.services import pose3d as P                                # noqa: E402
from app.services import asset3d_service as A3                      # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


# ══ A. détection par le sujet tapé ═════════════════════════════════════════════════════════════════════════════
print("A. sujet tapé")
CAS = {
    "a knight character": "personnage", "Une épée longue": "objet", "a dragon": "doute", "": "doute",
    "chevalier tenant une épée": "personnage", "a knight holding a sword": "personnage", "wooden barrels": "objet",
    "mandolin": "doute", "Mandoline et tabouret": "doute", "two Knights": "personnage", "Guerrière elfe": "personnage",
    "robot de combat": "doute", "a treasure chest": "objet", "prophète pieuvre": "personnage",
    "statue of a dragon": "doute", "TABLE EN CHÊNE": "objet", "humanoid robot": "personnage",
}
for s, attendu in CAS.items():
    check(f"A {s!r} -> {attendu}", P.classer_texte(s) == attendu, P.classer_texte(s))
check("A mot entier : « man » n'est pas trouvé dans « mandolin » ni « woman » dans « womanizer »",
      P.classer_texte("mandolin") == "doute" and P.classer_texte("womanizer") == "doute")

# ══ B. normalisation ═══════════════════════════════════════════════════════════════════════════════════════════
print("B. normalisation")
check("B pose prime sur tpose", P.normaliser({"pose": "a-pose", "tpose": True}) == "a-pose")
check("B « aucune » / « none » / « libre » -> \"\"",
      all(P.normaliser({"pose": v}) == "" for v in ("aucune", "none", "libre", "", "AUCUNE")))
check("B T-Pose en majuscules -> t-pose", P.normaliser({"pose": " T-Pose "}) == "t-pose")
check("B ancien booléen tpose vrai -> t-pose, faux -> \"\"",
      P.normaliser({"tpose": True}) == "t-pose" and P.normaliser({"tpose": False}) == "")
check("B corps muet -> None (comportement d'avant)", P.normaliser({}) is None and P.normaliser({"pose": None}) is None)
try:
    P.normaliser({"pose": "x-pose"}); check("B valeur inconnue refusée", False)
except ValueError as e:
    check("B valeur inconnue refusée", "Pose inconnue" in str(e))

# ══ C. état du choix ═══════════════════════════════════════════════════════════════════════════════════════════
print("C. état du choix")
check("C modes relevés moteur par moteur",
      {e: P.mode_moteur(e) for e in A3.ENGINES} == {"tripo": "vues", "tripo-h3.1": "vues", "rodin": "moteur",
                                                     "hunyuan": None, "trellis": None, "triposr": None,
                                                     "hunyuan-local": None,
                                                     # t390 : pose native pour Rodin 2.5 et Meshy 7.1, rien ailleurs
                                                     "tripo-p2": None, "tripo-p1": None, "hunyuan-3.1": None,
                                                     "trellis-2": None, "rodin-2.5": "moteur", "meshy-7.1": "moteur"}, str({e: P.mode_moteur(e) for e in A3.ENGINES}))
check("C meshy (3D Studio) : paramètre natif pose_mode", P.mode_moteur("meshy") == "moteur")
e = P.etat("rodin", False, "a knight")
check("C rodin + personnage : actif, sans avertissement", e["actif"] and e["raison"] == "" and e["avertissement"] == "")
e = P.etat("rodin", False, "a sword")
check("C rodin + objet : grisé, raison objet", not e["actif"] and e["raison"] == "objet" and e["sujet"] == "objet")
e = P.etat("trellis", True, "a knight")
check("C trellis : grisé, raison moteur (même pour un personnage)", not e["actif"] and e["raison"] == "moteur")
e = P.etat("hunyuan", False, "a sword")
check("C le moteur passe avant le sujet", e["raison"] == "moteur")
e = P.etat("tripo", False, "a knight")
check("C tripo sans vues : grisé, raison vues", not e["actif"] and e["raison"] == "vues")
e = P.etat("tripo-h3.1", True, "a knight")
check("C tripo-h3.1 avec vues : actif", e["actif"] and e["mode"] == "vues")
e = P.etat("rodin", False, "a dragon")
check("C doute : choix proposé AVEC avertissement", e["actif"] and e["avertissement"] == "doute")
e = P.etat("rodin", False, "")
check("C sujet vide : doute, texte None", e["sujet"] == "doute" and e["texte"] is None and e["avertissement"] == "doute")
Image.new("RGB", (64, 64), (200, 30, 30)).save(settings.images_path / "chevalier.png")
Image.new("RGB", (64, 64), (30, 200, 30)).save(settings.images_path / "tonneau.png")
check("C doute + image non classée : vision proposée",
      P.etat("rodin", False, "", "chevalier.png")["vision_proposee"] is True)
check("C pas de vision proposée sans image, ni pour une image absente",
      P.etat("rodin", False, "")["vision_proposee"] is False
      and P.etat("rodin", False, "", "absente.png")["vision_proposee"] is False)
check("C pas de vision proposée quand le texte tranche", P.etat("rodin", False, "a knight", "chevalier.png")["vision_proposee"] is False)
check("C pas d'avertissement quand le choix est grisé", P.etat("trellis", False, "a dragon")["avertissement"] == "")

# ══ D. transmission aux moteurs ════════════════════════════════════════════════════════════════════════════════
print("D. transmission")
for pose in ("t-pose", "a-pose"):
    v = A3.view_prompts(4, "a knight", pose)
    check(f"D {pose} : la phrase sur les 4 vues", all(P.PHRASES[pose] in x for x in v))
    check(f"D {pose} : l'autre pose n'apparaît pas", not any(("T-pose" if pose == "a-pose" else "A-pose") in x for x in v))
v = A3.view_prompts(4, "a barrel", "")
check("D aucune : pas un mot de pose", not any("pose" in x.lower() for x in v), v[0])
check("D aucune : la face reste « front view », cadrage intact",
      v[0].startswith("a barrel, front view, ") and all("orthographic framing" in x for x in v))
check("D sans pose (appelant d'avant) : l'ancien « front view, T-pose » sur la face seule",
      "front view, T-pose" in A3.view_prompts(2, "x")[0] and "T-pose" not in A3.view_prompts(2, "x")[1])
r = A3.build_engine_args("rodin", ["u"], {"pose": "a-pose"})
check("D rodin a-pose : TAPose + prompt A-pose", r["TAPose"] is True and r["prompt"] == P.PHRASES["a-pose"])
r = A3.build_engine_args("rodin", ["u"], {"pose": ""})
check("D rodin aucune : TAPose faux, aucun prompt", r["TAPose"] is False and "prompt" not in r)
r = A3.build_engine_args("rodin", ["u"], {"tpose": True})
check("D rodin ancien tpose : TAPose + prompt T-pose", r["TAPose"] is True and r["prompt"] == P.PHRASES["t-pose"])
for eng in ("tripo", "tripo-h3.1", "hunyuan", "trellis", "triposr", "hunyuan-local"):
    a = A3.build_engine_args(eng, ["u"], {"pose": "t-pose"})
    check(f"D {eng} : aucun paramètre de pose inventé",
          not any(k.lower() in ("tapose", "pose", "pose_mode", "prompt") for k in a), str(a))

# ══ D bis. l'adaptateur Rodin au schéma fal (Hyper3dRodinInput relu le 29/10/2026) ══════════════════════════════════
print("D bis. Rodin au schéma fal")
SCHEMA_RODIN = {"TAPose", "addons", "bbox_condition", "condition_mode", "geometry_file_format", "input_image_urls",
                "material", "prompt", "quality", "seed", "tier", "use_hyper"}
for o in ({}, {"pose": "t-pose", "quality": "hd"}, {"pose": "", "quality": "low", "format": "fbx"}):
    a = A3.build_engine_args("rodin", ["u1", "u2"], o)
    check(f"D2 rodin {o} : aucune clé hors schéma", set(a) <= SCHEMA_RODIN, str(sorted(set(a) - SCHEMA_RODIN)))
QUAL = {None: "medium", "medium": "medium", "high": "high", "hd": "high", "HD": "high", "low": "low",
        "extra-low": "extra-low", "ultra": "medium", "": "medium"}
for q, attendu in QUAL.items():
    a = A3.build_engine_args("rodin", ["u"], {} if q is None else {"quality": q})
    check(f"D2 rodin qualité {q!r} -> quality={attendu}", a.get("quality") == attendu, str(a.get("quality")))
a = A3.build_engine_args("rodin", ["u"], {"quality": "high", "format": "obj"})
check("D2 rodin : format et matériau transmis", a["geometry_file_format"] == "obj" and a["material"] == "PBR"
      and a["input_image_urls"] == ["u"])

# ══ E. routes ══════════════════════════════════════════════════════════════════════════════════════════════════
print("E. routes")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402


def _faux_download(url, dest, timeout=120):
    dest.write_bytes(b"glTF-faux")
    return True


A3._download = _faux_download
from app.services.storage import init_db                            # noqa: E402
asyncio.run(init_db())                                              # la table des jobs existe
c = TestClient(app)


def post3d(**kw):
    CALLS.clear()
    corps = {"engine": "rodin", "image_filename": "chevalier.png", "subject": "a knight", "multiview": False,
             "textures": True, "formats": ["glb"], **kw}
    return c.post("/api/assets/3d", json=corps)


r = post3d(engine="trellis", pose="t-pose")
check("E trellis + T-pose : 400, aucun contact fal", r.status_code == 400 and not CALLS, f"{r.status_code} {r.text[:200]}")
r = post3d(subject="a wooden barrel", pose="a-pose")
check("E sujet objet + A-pose : 400 « n'est pas un personnage »",
      r.status_code == 400 and "personnage" in r.json()["detail"] and not CALLS, r.text[:200])
r = post3d(engine="tripo", pose="t-pose", multiview=False)
check("E tripo sans vues + T-pose : 400 « vues multiples »",
      r.status_code == 400 and "vues multiples" in r.json()["detail"], r.text[:200])
r = post3d(pose="z-pose")
check("E pose inconnue : 400", r.status_code == 400 and "Pose inconnue" in r.json()["detail"])
r = post3d(engine="trellis", pose="")
check("E « Aucune » passe sur n'importe quel moteur", r.status_code == 200, r.text[:200])
r = post3d(pose="a-pose")
rodin = [x for x in CALLS if x["model"] == "fal-ai/hyper3d/rodin"]
check("E rodin + A-pose : 200 et le moteur reçoit TAPose + prompt A-pose",
      r.status_code == 200 and rodin and rodin[0]["arguments"]["TAPose"] is True
      and rodin[0]["arguments"]["prompt"] == P.PHRASES["a-pose"], str(rodin)[:300])
r = post3d(engine="tripo-h3.1", pose="t-pose", multiview=True, views=2)
vues = [x for x in CALLS if "seedream" in x["model"]]
check("E tripo-h3.1 + vues + T-pose : chaque vue Seedream reçoit la phrase T-pose",
      r.status_code == 200 and len(vues) == 2 and all(P.PHRASES["t-pose"] in x["arguments"]["prompt"] for x in vues),
      str(vues)[:300])
jobs = sorted((settings.outputs_path / "assets3d").glob("*/asset.json"), key=lambda p: p.stat().st_mtime)
man = json.loads(jobs[-1].read_text(encoding="utf-8"))
check("E le manifeste garde la pose (et tpose compatible)", man.get("pose") == "t-pose" and man.get("tpose") is True,
      str({k: man.get(k) for k in ("pose", "tpose")}))
r = post3d(engine="tripo", tpose=False, multiview=True, views=1)
vues = [x for x in CALLS if "seedream" in x["model"]]
check("E ancien corps tpose:false = « Aucune » : plus de T-pose imposée à la face",
      r.status_code == 200 and vues and "T-pose" not in vues[0]["arguments"]["prompt"], str(vues)[:200])
eng = {m["id"]: m for m in c.get("/api/assets3d/engines").json()["engines"]}
check("E /assets3d/engines expose le mode de pose", eng["rodin"]["pose"] == "moteur" and eng["tripo"]["pose"] == "vues"
      and eng["trellis"]["pose"] is None)
r = c.get("/api/assets3d/pose", params={"engine": "tripo", "multiview": "true", "subject": "une épée"})
check("E GET /pose : état gratuit (objet -> grisé)", r.status_code == 200 and r.json()["raison"] == "objet", r.text[:200])
CALLS.clear()
r = c.post("/api/assets/3d/views", json={"engine": "tripo-h3.1", "image_filename": "chevalier.png",
                                          "subject": "a barrel", "views": 2, "pose": "t-pose"})
check("E POST /assets/3d/views : la même règle (objet refusé), rien d'envoyé",
      r.status_code == 400 and not CALLS, r.text[:200])

# ══ F. classification vision ═══════════════════════════════════════════════════════════════════════════════════
print("F. vision")
from app.services import moteurs_texte as MT                         # noqa: E402
TIRS = []


async def _faux_tirer_garde(moteur, modele, prompt, systeme, max_tokens, *, categorie, timeout, images):
    TIRS.append({"categorie": categorie, "images": len(images), "mime": images[0]["mime"]})
    return REPONSE[0]


REPONSE = ["personnage"]
MT.configure = lambda m: True
MT.vision = lambda m, modele=None: True
MT.modele_sain = lambda m: "claude-test"
MT.nom = lambda m: "Claude"
MT.tirer_garde = _faux_tirer_garde
P._cout = lambda modele: 0.0123
d = c.get("/api/assets3d/pose/devis").json()
check("F devis gratuit : 0.0123 USD, disponible", d["usd"] == 0.0123 and d["disponible"] is True and not TIRS, str(d))
r = c.post("/api/assets3d/pose/classer", json={"image_filename": "chevalier.png"})
check("F sans confirme_cout : 409 avec le devis, rien d'envoyé",
      r.status_code == 409 and r.json()["detail"]["code"] == "confirme_cout" and not TIRS, r.text[:200])
r = c.post("/api/assets3d/pose/classer", json={"image_filename": "chevalier.png", "confirme_cout": True,
                                                "max_usd": 0.001})
check("F coût au-delà de l'accord : 409 {usd}, rien d'envoyé",
      r.status_code == 409 and r.json()["detail"]["usd"] == 0.0123 and not TIRS, r.text[:200])
r = c.post("/api/assets3d/pose/classer", json={"image_filename": "chevalier.png", "confirme_cout": True})
check("F accord sans montant : 400", r.status_code == 400 and not TIRS, r.text[:200])
r = c.post("/api/assets3d/pose/classer", json={"image_filename": "chevalier.png", "confirme_cout": True,
                                                "max_usd": 0.02, "engine": "rodin"})
check("F accord : un tir, catégorie « moteurs3d », une image JPEG",
      r.status_code == 200 and TIRS == [{"categorie": "moteurs3d", "images": 1, "mime": "image/jpeg"}], r.text[:200])
check("F la classe rendue et l'état recalculé", r.json()["classe"] == "personnage" and r.json()["usd"] == 0.0123
      and r.json()["etat"]["vision"] == "personnage")
r = c.post("/api/assets3d/pose/classer", json={"image_filename": "chevalier.png"})
check("F une fois par image : déjà classée -> rendue sans tir ni accord", r.status_code == 200 and r.json()["deja"]
      and r.json()["usd"] == 0.0 and len(TIRS) == 1, r.text[:200])
(settings.images_path / "copie.png").write_bytes((settings.images_path / "chevalier.png").read_bytes())
check("F le cache suit les OCTETS, pas le nom", P.classe_vision("copie.png") == "personnage")
e = P.etat("rodin", False, "", "chevalier.png")
check("F vision personnage : choix actif sans avertissement", e["actif"] and e["avertissement"] == ""
      and e["vision_proposee"] is False)
check("F texte objet + vision personnage : personnage (D6 : texte OU vision)",
      P.etat("rodin", False, "a sword", "chevalier.png")["actif"])
REPONSE[0] = "Objet."
r = c.post("/api/assets3d/pose/classer", json={"image_filename": "tonneau.png", "confirme_cout": True, "max_usd": 0.02})
check("F réponse « Objet. » lue comme objet ; le sujet vide devient grisé",
      r.json()["classe"] == "objet" and P.etat("rodin", False, "", "tonneau.png")["raison"] == "objet", r.text[:200])
check("F réponse hors des trois mots -> doute", P.lire_classe("je pense que c'est un chat") == "doute"
      and P.lire_classe("personnage") == "personnage")
check("F seul le PREMIER mot compte : « objet, pas un personnage » reste objet",
      P.lire_classe("objet, pas un personnage") == "objet" and P.lire_classe("Doute : peut-être un objet") == "doute")
r = c.post("/api/assets/3d", json={"engine": "rodin", "image_filename": "tonneau.png", "subject": "",
                                   "pose": "t-pose", "formats": ["glb"]})
check("F la route refuse une pose sur une image classée objet", r.status_code == 400, r.text[:200])
MT.configure = lambda m: False
Image.new("RGB", (64, 64), (1, 2, 3)).save(settings.images_path / "neuve.png")
TIRS.clear()
r = c.post("/api/assets3d/pose/classer", json={"image_filename": "neuve.png", "confirme_cout": True, "max_usd": 1})
check("F Claude non configuré : 503, aucun tir", r.status_code == 503 and not TIRS, r.text[:200])
check("F devis sans clé : indisponible, raison « cle », 0 USD",
      c.get("/api/assets3d/pose/devis").json() == {"usd": 0.0, "moteur": "anthropic", "nom": "Claude",
                                                   "disponible": False, "raison": "cle"})
r = c.post("/api/assets3d/pose/classer", json={"image_filename": "../t.db", "confirme_cout": True, "max_usd": 1})
check("F image hors Bibliothèque : 404", r.status_code == 404, r.text[:200])

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
