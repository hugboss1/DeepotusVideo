# -*- coding: utf-8 -*-
"""t323 (Compagnon M6, 26/11/2026) — la capture du téléphone déposée au PC (écriture n° 5) et le skin lu (lecture n° 6).
Banc-miroir : vraies requêtes depuis une IP du réseau local avec un vrai jeton d'appareil, fichiers relus. Aucun réseau.
  T1  témoin : la base (t322, 29f39fc6) n'a pas ces routes
  O1  ouvrir : sans jeton 401 ; déclaration invalide 400 ; mime 415 ; même empreinte = même session (idempotent)
  M1  morceaux dans l'ordre ; un morceau déjà reçu rend « deja » sans rien écrire ; trop d'octets 409 ; reprise (`recus`)
  M2  un autre appareil ne voit pas la session (404)
  F1  terminer : sha256 faux -> 409 et la session reste ouverte ; juste -> copie Bibliothèque, job, index, recette
      origine telephone, piste des clics nettoyée, montage gardé ; rouvrir la même empreinte après clôture -> 409
  S1  skin : sans jeton 401 ; espace inconnu 404 ; le skin actif normalisé (format v1) et le contexte de l'espace
  E1  les trois écritures sont ouvertes au Wi-Fi, la lecture du skin n'est pas une écriture
Run (depuis backend/) : & $PY tests/test_sync_capture.py"""
import hashlib, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsynccap_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent)); sys.path.insert(0, str(_ICI))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                          # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "29f39fc6"
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/main.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 témoin : la base n'ouvre pas /api/sync/capture", r1.returncode == 0 and b"/api/sync/capture" not in r1.stdout)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import _jeton_appareil as JA                                        # noqa: E402
from app.services import capture as C, espaces as E                 # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
LAN = ("192.168.1.42", 50000)
VIDEO = b"\x00\x00\x00\x18ftypmp42" + os.urandom(3000)
A, B = VIDEO[:1500], VIDEO[1500:]
SHA = hashlib.sha256(VIDEO).hexdigest()
EMP = "e" * 64


def decl(**k):
    d = {"empreinte": EMP, "taille": len(VIDEO), "sha256": SHA, "mime": "video/mp4", "duree_ms": 4000,
         "cadre": {"largeur": 1080, "hauteur": 2400}, "options": {"voix": True, "camera": False, "clics": True}}
    d.update(k)
    return d


CLICS = {"version": 1, "evenements": [
    {"type": "ecran", "t": 0, "ecran": "boite"},
    {"type": "clic", "t": 1200, "x": 0.5, "y": 0.4, "bouton": 0, "ecran": "boite",
     "cible": {"balise": "button", "role": "button", "t": "Envoyer au PC", "i": "", "test_id": "envoyer"}},
    {"type": "clic", "t": 2000, "x": 0.2, "y": 0.9, "secret": True, "ecran": "archive", "cible": {"t": "mot de passe"}},
    {"type": "saisie", "t": 2100, "texte": "secret"}]}

with TestClient(app, client=("127.0.0.1", 50001)) as loc:
    E.lire()
    lan = TestClient(app, client=LAN)
    H = JA.entetes(app)
    H2 = JA.entetes(app, ip="192.168.1.43")

    print("[O] ouvrir")
    check("O1a sans jeton : 401", lan.post("/api/sync/capture", json=decl()).status_code == 401)
    check("O1b empreinte invalide : 400", lan.post("/api/sync/capture", headers=H, json=decl(empreinte="x")).status_code == 400)
    check("O1c autre format : 415", lan.post("/api/sync/capture", headers=H, json=decl(mime="video/webm")).status_code == 415)
    r = lan.post("/api/sync/capture", headers=H, json=decl())
    cid = (r.json() or {}).get("id")
    check("O1d session ouverte en mode telephone", r.status_code == 200 and r.json().get("recus") == 0
          and C._lire_session(cid)["options"]["mode"] == "telephone", r.text[:200])
    r = lan.post("/api/sync/capture", headers=H, json=decl())
    check("O1e même empreinte : même session", r.json().get("id") == cid)

    print("\n[M] morceaux")
    HV = {**H, "Content-Type": "video/mp4"}
    r = lan.post(f"/api/sync/capture/{cid}/morceau/0", headers=HV, content=A)
    check("M1a morceau 0 reçu", r.status_code == 200 and r.json().get("octets") == len(A), r.text[:200])
    r = lan.post(f"/api/sync/capture/{cid}/morceau/0", headers=HV, content=A)
    check("M1b morceau 0 renvoyé : deja, rien d'écrit", r.json().get("deja") is True
          and C.chemin_piste(cid, "scene").stat().st_size == len(A))
    check("M1c reprise : rouvrir dit 1 morceau reçu", lan.post("/api/sync/capture", headers=H, json=decl()).json().get("recus") == 1)
    r = lan.post(f"/api/sync/capture/{cid}/morceau/1", headers=HV, content=B + b"trop")
    check("M1d plus d'octets que la taille annoncée : 409", r.status_code == 409)
    check("M2 un autre appareil ne voit pas la session : 404",
          lan.post(f"/api/sync/capture/{cid}/morceau/1", headers={**H2, "Content-Type": "video/mp4"}, content=B).status_code == 404)

    print("\n[F] terminer")
    r = lan.post(f"/api/sync/capture/{cid}/terminer", headers=H, json={"clics": CLICS})
    check("F1a fichier incomplet : 409, session encore ouverte", r.status_code == 409 and C._lire_session(cid)["etat"] == "en_cours")
    r = lan.post(f"/api/sync/capture/{cid}/morceau/1", headers=HV, content=B)
    check("F1b dernier morceau", r.status_code == 200 and r.json().get("octets") == len(VIDEO))
    r = lan.post(f"/api/sync/capture/{cid}/terminer", headers=H,
                 json={"clics": CLICS, "montage": {"version": 1, "coupe": [0, 3000]}, "titre": "Démo de la Boîte"})
    b = r.json() if r.status_code == 200 else {}
    dest = _tmp / "outputs" / "captures" / str(b.get("fichier"))
    check("F1c clôture : fichier copié identique, job créé", r.status_code == 200 and dest.is_file()
          and hashlib.sha256(dest.read_bytes()).hexdigest() == SHA and b.get("job_id"), r.text[:300])
    lu = C.lire(cid)["clics"]
    types = [e["type"] for e in lu["evenements"]]
    check("F1d piste nettoyée : écran + 2 clics, la saisie retirée, le clic secret sans libellé",
          types == ["ecran", "clic", "clic"] and lu["evenements"][2].get("secret") is True
          and lu["evenements"][2]["cible"]["t"] == "" and lu["cadre"]["mode"] == "telephone"
          and lu["evenements"][1]["cible"].get("test_id") == "envoyer" and "test_id" not in lu["evenements"][2]["cible"], str(lu)[:300])
    check("F1e montage du téléphone gardé", json.loads((C._dossier(cid) / "montage_telephone.json").read_text("utf-8"))["coupe"] == [0, 3000])
    check("F1f rouvrir la même empreinte après clôture : 409", lan.post("/api/sync/capture", headers=H, json=decl()).status_code == 409)

    import asyncio
    from app.services.storage import LibraryAsset, async_session_factory

    async def _rec():
        async with async_session_factory() as s:
            row = await s.get(LibraryAsset, dest.name)
            return json.loads(row.recette) if row and row.recette else {}
    rec = asyncio.run(_rec())
    check("F1g index capture : recette origine telephone, appareil, empreinte", rec.get("origine") == "telephone"
          and rec.get("empreinte") == EMP and rec.get("mode") == "telephone", str(rec)[:300])

    print("\n[S] skin")
    check("S1a sans jeton : 401", lan.get("/api/sync/skin").status_code == 401)
    check("S1b espace inconnu : 404", lan.get("/api/sync/skin?espace=inconnu", headers=H).status_code == 404)
    r = lan.get("/api/sync/skin?espace=deepotus", headers=H)
    sk = (r.json() or {}).get("skin") or {}
    check("S1c skin actif normalisé (format v1) et contexte de l'espace", r.status_code == 200 and sk.get("version") == 1
          and sk.get("format") and r.json()["contexte"]["espace"]["id"] == "deepotus", r.text[:300])

    check("E1 trois écritures ouvertes, la lecture du skin n'en est pas une",
          {("POST", "/api/sync/capture"), ("POST", "/api/sync/capture/{cid}/morceau/{n}"), ("POST", "/api/sync/capture/{cid}/terminer")}
          <= _MAIN._ECRITURES_OUVERTES and not any("skin" in c for _m, c in _MAIN._ECRITURES_OUVERTES))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
