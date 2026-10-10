# -*- coding: utf-8 -*-
"""Plan mobile T12 + T13 (tache #58 du suivi, 01/10/2026) — le manifeste de la Bibliotheque et le depot verifie.
DECISIONS DE L'UTILISATEUR (01/10) : les ecritures du telephone sont ouvertes au reseau local UNE PAR UNE — ici
POST /api/sync/depot, et elle seule ; l'appareil est TOUJOURS celui du jeton (jamais un champ du corps). Le depot est
garde comme /images/upload (PR #96 : Pillow decide), borne en taille, verifie par sha256, et ne laisse RIEN en cas
d'echec. Le telechargement repris passe par GET /api/images/{nom} (FileResponse : Range), deja existant.
Corrections du plan (03/09) : l'appareil venait du formulaire ; aucune garde de contenu (un .html servi depuis
/api/images) ; lecture non bornee ; homonymes « _2 » au lieu de « -1 » ; mode incremental aveugle aux suppressions.
Banc-miroir : vraies requetes portant une IP du reseau local, lignes relues dans la base, fichiers relus sur disque.
Temoin positif : la base (27b839fa) n'a ni sync_index ni la source « mobile », et /sync/depot n'y est pas ouvert.
Run (depuis backend/) : & $PY tests/test_sync_manifeste.py"""
import hashlib, io, json, os, pathlib, sqlite3, subprocess, sys, tempfile, time
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzsyncman_"))
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


BASE = "27b839fa"
r0 = subprocess.run(["git", "cat-file", "-e", f"{BASE}:backend/app/services/sync_index.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/services/library_index.py"], capture_output=True, cwd=str(_ICI.parent))
r2 = subprocess.run(["git", "show", f"{BASE}:backend/app/main.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni sync_index, ni la source mobile, ni /sync/depot ouvert",
      r0.returncode != 0 and r1.returncode == 0 and b'"mobile"' not in r1.stdout
      and r2.returncode == 0 and b"/api/sync/depot" not in r2.stdout)

from fastapi.testclient import TestClient                           # noqa: E402
from PIL import Image                                               # noqa: E402
from app.main import app                                            # noqa: E402
import app.main as _MAIN                                            # noqa: E402
import _jeton_appareil as JA                                        # noqa: E402


async def _boucle_coupee():
    return None
_MAIN.schedule_loop = _boucle_coupee

IMAGES = _tmp / "images"
RECETTES = _tmp / "outputs" / "_sync" / "recettes"
LAN = ("192.168.1.42", 50000)


def png(couleur, taille=(8, 8)) -> bytes:
    b = io.BytesIO()
    Image.new("RGB", taille, couleur).save(b, "PNG")
    return b.getvalue()


def js(r) -> dict:
    """Le corps JSON, ou {} : une route absente rend la page HTML (catch-all) — le banc doit ECHOUER, pas planter."""
    try:
        v = r.json()
        return v if isinstance(v, dict) else {"_liste": v}
    except Exception:
        return {}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def actif(nom):
    cx = sqlite3.connect(str(_DB))
    try:
        return cx.execute("SELECT source, origin FROM library_assets WHERE filename=?", (nom,)).fetchone()
    finally:
        cx.close()


def fichiers():
    return sorted(p.name for p in IMAGES.iterdir())


A, B, C = png("red"), png("blue", (6, 6)), png("green", (5, 5))
with TestClient(app, client=("127.0.0.1", 50000), raise_server_exceptions=False) as loc:
    (IMAGES / "gen_aa11bb22.png").write_bytes(A)
    (IMAGES / "photo_vacances.jpg").write_bytes(B)
    (IMAGES / "notice.txt").write_text("pas une image", encoding="utf-8")
    import asyncio
    from app.services import library_index as LI
    asyncio.run(LI.noter(["gen_aa11bb22.png"], "generation"))       # depot connu ; la photo reste a l'heuristique
    H = JA.entetes(app, LAN[0])
    lan = TestClient(app, client=LAN, raise_server_exceptions=False)
    moi = [a for a in loc.get("/api/devices").json()["appareils"] if not a["revoque"]][0]

    print("\n[M] le manifeste")
    check("M1 sans jeton depuis le Wi-Fi : 401", lan.get("/api/sync/manifeste").status_code == 401)
    check("M1b sans jeton MEME depuis la boucle locale : 401 (le manifeste est celui d'un appareil, comme le lot)",
          loc.get("/api/sync/manifeste").status_code == 401)
    r = lan.get("/api/sync/manifeste", headers=H)
    m = js(r) if r.status_code == 200 else {}
    noms = [e["nom"] for e in m.get("index", [])]
    check("M2 protocole 1 ; seules les images (pas le .txt)", r.status_code == 200 and m.get("protocole") == 1
          and sorted(noms) == ["gen_aa11bb22.png", "photo_vacances.jpg"], f"{r.status_code} {noms}")
    e = {x["nom"]: x for x in m.get("index", [])}
    ga, ph = e.get("gen_aa11bb22.png", {}), e.get("photo_vacances.jpg", {})
    check("M3 chaque entree : taille, sha256 EXACT, provenance (depot connu / heuristique), url de reprise",
          ga.get("taille") == len(A) and ga.get("sha256") == sha(A) and ga.get("source") == "generation"
          and ga.get("origine") == "depot" and ga.get("url") == "/api/images/gen_aa11bb22.png"
          and ph.get("sha256") == sha(B) and ph.get("source") == "inconnu" and ph.get("origine") == "heuristique", str(e)[:400])
    check("M4 poids_index = somme de l'index rendu ; genere_a en UTC Z",
          m.get("poids_index") == len(A) + len(B) and str(m.get("genere_a", "")).endswith("Z"), str(m)[:200])
    check("M5 le manifeste ne porte aucun chemin du disque", str(_tmp).lower().replace("\\", "/") not in json.dumps(m).lower().replace("\\\\", "/"))

    time.sleep(1.1)
    t0 = datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + "Z"
    time.sleep(1.1)
    (IMAGES / "gen_ee55ff66.png").write_bytes(C)
    (IMAGES / "photo_vacances.jpg").unlink()
    r = lan.get(f"/api/sync/manifeste?depuis={t0}", headers=H)
    mi = js(r) if r.status_code == 200 else {}
    check("M6 incremental : SEUL le neuf dans l'index", [x["nom"] for x in mi.get("index", [])] == ["gen_ee55ff66.png"], str(mi)[:300])
    check("M7 incremental : `noms` dit TOUT ce qui existe (une suppression se voit, un vieux mtime aussi)",
          mi.get("noms") == ["gen_aa11bb22.png", "gen_ee55ff66.png"], str(mi.get("noms")))
    r = lan.get("/api/sync/manifeste?depuis=pas-une-date", headers=H)
    check("M8 `depuis` illisible : l'index complet, pas une 500", r.status_code == 200
          and sorted(x["nom"] for x in js(r).get("index", [])) == ["gen_aa11bb22.png", "gen_ee55ff66.png"], str(r.status_code))
    g = lan.get("/api/images/gen_aa11bb22.png", headers=H)
    gr = lan.get("/api/images/gen_aa11bb22.png", headers={**H, "Range": "bytes=10-29"})
    check("M9 reprise : l'url du manifeste rend les octets exacts, et une plage (206, 20 o)",
          g.status_code == 200 and g.content == A and gr.status_code == 206 and gr.content == A[10:30], f"{g.status_code} {gr.status_code}")

    print("\n[P] projets epingles (decides sur le PC)")
    check("P1 epingler depuis le Wi-Fi : 403 (ecriture non ouverte)",
          lan.post("/api/sync/projet", headers=H, json={"nom": "x", "fichiers": ["a.png"]}).status_code == 403)
    check("P2 nom vide : 400", loc.post("/api/sync/projet", json={"nom": "  ", "fichiers": []}).status_code == 400)
    r = loc.post("/api/sync/projet", json={"nom": "campagne-octobre", "fichiers": ["../../gen_aa11bb22.png", "gen_ee55ff66.png", ""]})
    check("P3 epingler sur le PC : noms nus (pas de chemin), tries", r.status_code == 200
          and js(r) == {"nom": "campagne-octobre", "fichiers": ["gen_aa11bb22.png", "gen_ee55ff66.png"]}, r.text[:200])
    pj = js(lan.get("/api/sync/manifeste", headers=H)).get("projets")
    check("P4 le manifeste porte le projet, EN ENTIER", pj == [{"nom": "campagne-octobre", "fichiers": ["gen_aa11bb22.png", "gen_ee55ff66.png"],
                                                               "entier": True}], str(pj))

    print("\n[D] le depot du telephone")
    D = png("purple", (7, 7))
    def deposer(nom, contenu, empreinte=None, recette=None, h=H, client=lan, extra=None):
        data = {"sha256": empreinte if empreinte is not None else sha(contenu)}
        if recette is not None:
            data["recette"] = recette if isinstance(recette, str) else json.dumps(recette)
        if extra:
            data.update(extra)
        return client.post("/api/sync/depot", headers=h, files={"file": (nom, contenu, "image/png")}, data=data)
    check("D1 sans jeton depuis le Wi-Fi : 401", deposer("mob_a.png", D, h={}).status_code == 401)
    rec = {"moteur": "fal/flux", "prompt": "un poulpe", "cout_usd": 0.03, "parent": "gen_aa11bb22.png", "relation": "retouche",
           "appareil": {"id": "faux-id", "nom": "USURPATEUR"}}
    r = deposer("mob_a.png", D, recette=rec, extra={"appareil": "USURPATEUR"})
    j = js(r) if r.status_code == 200 else {}
    check("D2 un depot correct : 200, octets exacts sur disque, nom rendu", r.status_code == 200 and j.get("filename") == "mob_a.png"
          and (IMAGES / "mob_a.png").read_bytes() == D and j.get("sha256") == sha(D) and j.get("taille") == len(D), r.text[:300])
    check("D3 provenance : source « mobile », origine depot", actif("mob_a.png") == ("mobile", "depot"), str(actif("mob_a.png")))
    lu = json.loads((RECETTES / "mob_a.png.json").read_text(encoding="utf-8")) if (RECETTES / "mob_a.png.json").is_file() else {}
    check("D4 la recette est gardee, avec l'appareil DU JETON (un « appareil » dans la recette OU le corps est ignore)",
          lu.get("moteur") == "fal/flux" and lu.get("parent") == "gen_aa11bb22.png" and lu.get("appareil") == {"id": moi["id"], "nom": moi["nom"]}
          and "USURPATEUR" not in json.dumps(lu), str(lu)[:300])
    check("D5 la recette ne va PAS dans le dossier des images", not any(n.endswith(".json") for n in fichiers()), str(fichiers()))
    avant = fichiers()
    r = deposer("mob_b.png", D, empreinte="0" * 64)
    check("D6 empreinte fausse : 422, RIEN laisse (ni fichier, ni .part)", r.status_code == 422 and "sha256" in r.text and fichiers() == avant,
          f"{r.status_code} {fichiers()}")
    r = deposer("mob_c.png", b"<html><script>alert(1)</script></html>")
    check("D7 un .png qui contient du HTML : 415, rien ecrit", r.status_code == 415 and fichiers() == avant, f"{r.status_code} {fichiers()}")
    r = deposer("mob_d.html", D)
    check("D8 une extension qui n'est pas d'image : 400, rien ecrit", r.status_code == 400 and fichiers() == avant, f"{r.status_code}")
    try:
        import app.services.sync_index as SI
        garde, SI.TAILLE_MAX = SI.TAILLE_MAX, 64
        try:
            r = deposer("mob_e.png", D)
        finally:
            SI.TAILLE_MAX = garde
        check("D9 au-dela de la taille maximale : 413, rien ecrit", r.status_code == 413 and fichiers() == avant, f"{r.status_code}")
        garde, SI.TAILLE_MAX = SI.TAILLE_MAX, 64
        try:
            r = deposer("mob_e2.png", b"<html>" + b"x" * 200 + b"</html>")
        finally:
            SI.TAILLE_MAX = garde
        check("D9b la taille est bornee AVANT tout decodage : un gros non-image -> 413 (pas 415)", r.status_code == 413, f"{r.status_code}")
        vrai_replace = SI.os.replace
        def _panne(*_a, **_k):
            raise OSError("disque plein (simule)")
        SI.os.replace = _panne
        try:
            r = deposer("mob_panne.png", png("navy"))
        finally:
            SI.os.replace = vrai_replace
        check("D9c panne au moment d'ecrire : erreur, et RIEN ne reste (ni l'image, ni son .part)",
              r.status_code >= 500 and fichiers() == avant, f"{r.status_code} {fichiers()}")
    except ImportError as e:
        check("D9 au-dela de la taille maximale : 413, rien ecrit", False, repr(e))
    r = deposer("mob_a.png", D)
    check("D10 le MEME fichier redepose (reprise apres coupure) : idempotent, pas de doublon",
          r.status_code == 200 and js(r).get("filename") == "mob_a.png" and js(r).get("deja") is True and fichiers() == avant, r.text[:200])
    E = png("orange", (9, 9))
    r = deposer("mob_a.png", E)
    check("D11 homonyme d'un AUTRE contenu : « mob_a-1.png », l'original intact", r.status_code == 200 and js(r).get("filename") == "mob_a-1.png"
          and (IMAGES / "mob_a.png").read_bytes() == D and (IMAGES / "mob_a-1.png").read_bytes() == E, r.text[:200])
    r = deposer("../../evil.png", png("black"))
    check("D12 un nom avec chemin : depose sous son nom NU, dans le dossier des images", r.status_code == 200
          and js(r).get("filename") == "evil.png" and (IMAGES / "evil.png").is_file() and not (_tmp / "evil.png").exists(), r.text[:200])
    r = deposer("mob_f.png", png("white"), recette="{pas du json")
    check("D13 recette illisible : 400, rien ecrit", r.status_code == 400 and not (IMAGES / "mob_f.png").exists(), f"{r.status_code}")
    check("D14 /sync/depot rejoint les ecritures ouvertes (et /sync/depenses, tache #58 T18 — rien d'autre)",
          _MAIN._ECRITURES_OUVERTES == frozenset({("POST", "/api/pair/claim"), ("POST", "/api/sync/lot/etat"), ("POST", "/api/sync/depot"), ("POST", "/api/sync/depenses"), ("POST", "/api/sync/chapitre/prendre"), ("POST", "/api/sync/chapitre/rendre"),
                                                 ("POST", "/api/avatar-live/sessions"), ("POST", "/api/avatar-live/sessions/fin"), ("POST", "/api/avatar-live/sessions/voix")}),   # t161 : + le Direct
          str(sorted(_MAIN._ECRITURES_OUVERTES)))
    check("D15 la source « mobile » est au catalogue", LI.SOURCES.get("mobile") == "Compagnon mobile")
    loc.post(f"/api/devices/{moi['id']}/revoke")
    check("D16 appareil revoque : 401, rien ecrit", deposer("mob_g.png", png("gray")).status_code == 401 and not (IMAGES / "mob_g.png").exists())

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
