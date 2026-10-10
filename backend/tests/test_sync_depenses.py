# -*- coding: utf-8 -*-
"""Plan mobile T18 (tache #58 du suivi, 02/10/2026) — les depenses du telephone COMPTEES par le PC.
DECISION DE L'UTILISATEUR (01/10) : les tirs payants faits depuis le telephone entrent dans la table `Depense`
(categorie « mobile ») — donc dans le plafond mensuel (#16) et le tableau reel/estime (#21) — et non dans un fichier a
part comme le voulait le plan (ils y auraient echappe au plafond). POST /api/sync/depenses est ouverte au reseau local
(decision « une par une ») ; l'appareil est celui du JETON. Chaque tir porte un identifiant du telephone : renvoye
apres une coupure, il n'est jamais compte deux fois. Le mois est celui de l'HEURE LOCALE du tir (comme mois_courant).
Banc-miroir : vraies requetes depuis une IP du reseau local avec un vrai jeton, lignes relues dans la base.
Temoin positif : la base (3c40b67e) n'a ni sync_depenses ni la route ouverte.
Run (depuis backend/) : & $PY tests/test_sync_depenses.py"""
import os, pathlib, sqlite3, subprocess, sys, tempfile, time
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsyncdep_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
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
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "3c40b67e"
r0 = subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/sync_depenses.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/main.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni sync_depenses ni /sync/depenses ouverte",
      r0.returncode != 0 and r1.returncode == 0 and b"/api/sync/depenses" not in r1.stdout)

from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import _jeton_appareil as JA                                        # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee
LAN = ("192.168.1.42", 50000)


def js(r) -> dict:
    try:
        v = r.json()
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def lignes():
    cx = sqlite3.connect(str(_DB))
    try:
        return cx.execute("SELECT moteur, categorie, op, estime_usd, reel_usd, mois, ref, quand FROM depenses ORDER BY id").fetchall()
    finally:
        cx.close()


def iso(d: datetime) -> str:
    return d.replace(microsecond=0).isoformat() + "Z"


NOW = datetime.utcnow()
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as loc:
    H = JA.entetes(app, LAN[0])
    lan = TestClient(app, client=LAN, raise_server_exceptions=False)
    moi = [a for a in loc.get("/api/devices").json()["appareils"] if not a["revoque"]][0]
    from app.services import plafonds as PL
    PL.enregistrer({"global_usd": 0, "par_moteur": {"fal": 1.0}, "alerte_pct": 80})
    tir = lambda i, usd, **k: {"id": i, "moteur": "fal", "op": "image", "estime_usd": usd, "quand": iso(NOW), **k}

    print("\n[A] acces")
    check("A1 sans jeton depuis le Wi-Fi : 401", lan.post("/api/sync/depenses", json={"tirs": [tir("t1", 0.3)]}).status_code == 401)
    check("A2 la route est ouverte au Wi-Fi, ELLE SEULE de plus",
          _MAIN._ECRITURES_OUVERTES == frozenset({("POST", "/api/pair/claim"), ("POST", "/api/sync/lot/etat"),
                                                  ("POST", "/api/sync/depot"), ("POST", "/api/sync/depenses"), ("POST", "/api/sync/chapitre/prendre"), ("POST", "/api/sync/chapitre/rendre"),
                                                  ("POST", "/api/avatar-live/sessions"), ("POST", "/api/avatar-live/sessions/fin"), ("POST", "/api/avatar-live/sessions/voix"), ("POST", "/api/avatar-live/recast/source"), ("POST", "/api/avatar-live/recast"), ("POST", "/api/avatar-live/voix"), ("POST", "/api/avatar-live/decor"), ("POST", "/api/avatar-live/direct/enregistrer"), ("POST", "/api/avatar-live/recast/finaliser")}), str(sorted(_MAIN._ECRITURES_OUVERTES)))   # t161 : + le Direct

    print("\n[F] fusion dans la table Depense")
    vieux = (NOW - timedelta(days=62)).replace(day=15, hour=12)
    r = lan.post("/api/sync/depenses", headers=H, json={"tirs": [
        tir("t1", 0.3), tir("t2", 0.55, reel_usd=0.5, op="retouche", categorie="IGNOREE"),
        {"id": "t3", "moteur": "elevenlabs", "op": "voix", "estime_usd": 0.12, "quand": iso(vieux)}]})
    j = js(r)
    L = lignes()
    check("F1 200 ; trois tirs inseres", r.status_code == 200 and sorted(j.get("inseres", [])) == ["t1", "t2", "t3"] and len(L) == 3, f"{r.status_code} {r.text[:200]}")
    pref = f"mobile:{moi['id'][:8]}:"
    t1 = next((l for l in L if l[6] == pref + "t1"), None)
    check("F2 une ligne : moteur, categorie « mobile » (jamais celle du corps), op, estime, ref de l'appareil du JETON",
          t1 is not None and t1[:5] == ("fal", "mobile", "image", 0.3, None) and all(l[1] == "mobile" for l in L), str(L))
    t2 = next((l for l in L if l[6] == pref + "t2"), None)
    check("F3 un reel connu est garde (effectif = reel)", t2 is not None and t2[4] == 0.5, str(t2))
    t3 = next((l for l in L if l[6] == pref + "t3"), None)
    attendu = vieux.replace(tzinfo=timezone.utc).astimezone().strftime("%Y-%m")
    check("F4 le mois est celui de l'HEURE LOCALE du tir, et `quand` est l'instant du tir", t3 is not None and t3[5] == attendu
          and str(t3[7]).startswith(vieux.strftime("%Y-%m-%d %H:%M")), f"{t3} attendu {attendu}")
    check("F5 le tir du jour compte au mois courant", t1 is not None and t1[5] == PL.mois_courant(), str(t1))

    print("\n[I] idempotence")
    r = lan.post("/api/sync/depenses", headers=H, json={"tirs": [tir("t1", 0.3), tir("t4", 0.05)]})
    j = js(r)
    check("I1 un tir renvoye (coupure) n'est PAS compte deux fois ; le neuf l'est",
          j.get("deja") == ["t1"] and j.get("inseres") == ["t4"] and len(lignes()) == 4, f"{r.text[:200]} {len(lignes())}")

    r = lan.post("/api/sync/depenses", headers=H, json={"tirs": [tir("t5", 0.01), tir("t5", 0.01)]})
    check("I2 le meme tir DEUX FOIS dans un envoi : compte une fois", js(r).get("inseres") == ["t5"] and js(r).get("deja") == ["t5"]
          and len(lignes()) == 5, r.text[:200])

    print("\n[P] plafond mensuel (#16)")
    e = j.get("plafonds", {})
    check("P1 la reponse dit l'etat du mois : fal a 0,85 $ sur 1 $ (seuil 80 %) -> en alerte", "fal" in e.get("alerte", []) and e.get("mois") == PL.mois_courant(), str(e))
    import asyncio
    et = asyncio.run(PL.etat())
    check("P2 les tirs du telephone sont DANS le cumul du plafond (effectif fal = 0,3 + 0,5 reel + 0,05 + 0,01)",
          abs(et["par_moteur"].get("fal", {}).get("effectif_usd", 0) - 0.86) < 1e-6, str(et["par_moteur"].get("fal")))
    tab = asyncio.run(PL.tableau())
    check("P3 et dans le tableau reel/estime (#21), categorie mobile", any(str(g.get("categorie")) == "mobile" for g in
          (tab.get("lignes") or tab.get("groupes") or [])), str(tab)[:300])

    print("\n[R] refus (rien d'ecrit pour un tir refuse)")
    avant = len(lignes())
    mauvais = [{"id": "", "moteur": "fal", "estime_usd": 0.1, "quand": iso(NOW)},
               {"id": "m2", "moteur": "", "estime_usd": 0.1, "quand": iso(NOW)},
               {"id": "m3", "moteur": "fal", "estime_usd": "beaucoup", "quand": iso(NOW)},
               {"id": "m4", "moteur": "fal", "estime_usd": -1, "quand": iso(NOW)},
               {"id": "m5", "moteur": "fal", "estime_usd": 1e9, "quand": iso(NOW)},
               {"id": "m6", "moteur": "fal", "estime_usd": 0.1, "quand": "hier"},
               {"id": "m7", "moteur": "fal", "estime_usd": 0.1, "quand": iso(NOW + timedelta(days=2))},
               {"id": "m8/../x", "moteur": "fal", "estime_usd": 0.1, "quand": iso(NOW)},
               {"id": "m9", "moteur": "fal", "estime_usd": 0, "quand": iso(NOW)},
               "pas un objet"]
    r = lan.post("/api/sync/depenses", headers=H, json={"tirs": mauvais})
    j = js(r)
    ref = {x.get("id"): x.get("raison") for x in j.get("refuses", [])}
    check("R1 chaque tir malforme est REFUSE avec sa raison, rien n'est ecrit", r.status_code == 200 and len(j.get("refuses", [])) == 10
          and len(lignes()) == avant and all(ref.values()), f"{r.status_code} {j}")
    check("R2 corps sans liste : 400", lan.post("/api/sync/depenses", headers=H, json={"tirs": "x"}).status_code == 400)
    r = lan.post("/api/sync/depenses", headers=H, json={"tirs": [tir(f"z{i}", 0.01) for i in range(201)]})
    check("R3 plus de 200 tirs d'un coup : 413, rien ecrit", r.status_code == 413 and len(lignes()) == avant, str(r.status_code))
    loc.post(f"/api/devices/{moi['id']}/revoke")
    check("R4 appareil revoque : 401, rien ecrit", lan.post("/api/sync/depenses", headers=H, json={"tirs": [tir("t9", 0.1)]}).status_code == 401
          and len(lignes()) == avant)

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
