# -*- coding: utf-8 -*-
"""Plan mobile T4 + T5 (tache #56 du suivi, PR 2/3, 01/10/2026) — la garde de jeton sur TOUTE route hors boucle locale,
les routes d'appairage, et HOST configurable jusqu'au lanceur. Mesure sur de VRAIES requetes (TestClient dont le
client porte l'IP voulue) et sur le VRAI lanceur (sa fonction de lecture de HOST executee par cscript, sans jamais
demarrer le backend).
Ecarts au plan, mesures le 01/10 :
  - la garde des ECRITURES locales (P1 #14, decision de l'utilisateur du 29/09) EXISTE deja : un jeton valide n'ouvre
    que les LECTURES ; la seule ecriture ouverte au reseau local est POST /api/pair/claim (_ECRITURES_OUVERTES) ;
  - launch-silent.vbs est en Option Explicit : le bloc du plan (variables non declarees) aurait EMPECHE l'app de
    demarrer -> fonction LireHote, executee ici par cscript.
Data-dir isole (aucune cle reelle). Temoin positif : la base (1f7c7e54) n'a ni /pair/claim ni la garde de jeton.
Run (depuis backend/) : & $PY tests/test_appairage_routes.py"""
import base64, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzgarde_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_ICI = pathlib.Path(__file__).resolve().parent
_RACINE = _ICI.parents[1]
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "1f7c7e54"
r0 = subprocess.run(["git", "show", f"{BASE}:backend/app/main.py"], capture_output=True, cwd=str(_ICI.parent))
r1 = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
check("T1 temoin : la base n'a ni la garde de jeton ni /pair/claim",
      r0.returncode == 0 and b"_device_token_guard" not in r0.stdout and b'"/pair/claim"' not in r1.stdout)

from fastapi.testclient import TestClient                           # noqa: E402
from starlette.routing import WebSocketRoute                        # noqa: E402
from app.main import app                                            # noqa: E402
from app.services import qrcode_min                                 # noqa: E402

LAN = ("192.168.1.42", 50000)
LOC = ("127.0.0.1", 50000)

with TestClient(app, client=LOC, raise_server_exceptions=False) as loc, \
        TestClient(app, client=LAN, raise_server_exceptions=False) as lan:
    print("\n[G] la garde de jeton")
    check("G1 boucle locale sans jeton : lecture 200", loc.get("/api/jobs").status_code == 200)
    r = lan.get("/api/jobs")
    check("G2 reseau local SANS jeton, lecture : 401 qui dit quoi faire", r.status_code == 401 and "jeton" in r.text.lower()
          and "Appareils" in r.text, r.text[:120])
    fermes = {p: lan.get(p).status_code for p in ("/", "/api/health", "/vectorlab/", "/guide/", "/api/route-qui-n-existe-pas")}
    check("G3 TOUTE route est fermee : page, sante, outils statiques, et meme une route inconnue (401, pas 404)",
          set(fermes.values()) == {401}, str(fermes))
    check("G4 /api/pair/start depuis le reseau local : 401 (le QR ne s'affiche que sur le PC)",
          lan.post("/api/pair/start").status_code == 401)

    print("\n[P] l'appairage")
    s = loc.post("/api/pair/start")
    sj = s.json() if s.status_code == 200 else {}
    png = base64.b64decode(sj.get("qr_png_b64", "") or b"")
    check("P1 pair/start (PC) : secret, URL dz1:// portant hote, port et secret, delai 300 s",
          s.status_code == 200 and len(sj.get("secret", "")) == 32
          and sj.get("url") == f"dz1://pair?h={sj.get('hote')}&p={sj.get('port')}&s={sj.get('secret')}"
          and sj.get("expire_dans_s") == 300, s.text[:200])
    check("P2 le QR rendu est un PNG, ET le PNG de l'URL rendue (meme encodeur, meme taille)",
          png[:8] == b"\x89PNG\r\n\x1a\n" and png == qrcode_min.png(sj.get("url", "x"), module=8, marge=4))
    c1 = lan.post("/api/pair/claim", json={"secret": sj.get("secret"), "nom": "iPhone de Oli"})
    jeton = c1.json().get("jeton", "") if c1.status_code == 200 else ""
    check("P3 pair/claim depuis le reseau local SANS jeton : 200, jeton de 64, fiche, protocole 1",
          c1.status_code == 200 and len(jeton) == 64 and c1.json().get("appareil", {}).get("nom") == "iPhone de Oli"
          and c1.json().get("protocole") == 1, c1.text[:200])
    c2 = lan.post("/api/pair/claim", json={"secret": sj.get("secret"), "nom": "bis"})
    check("P4 le meme secret une seconde fois : 403 qui le dit", c2.status_code == 403 and "consomm" in c2.text, c2.text[:120])
    check("P5 corps vide ou secret absent : 403, jamais 500",
          lan.post("/api/pair/claim", json={}).status_code == 403 and lan.post("/api/pair/claim").status_code in (403, 422))

    print("\n[J] le jeton")
    H = {"Authorization": f"Bearer {jeton}"}
    check("J1 reseau local + jeton : la lecture passe (200)", lan.get("/api/jobs", headers=H).status_code == 200)
    check("J2 « bearer » en minuscules accepte ; jeton faux, sans « Bearer », ou tronque : 401",
          lan.get("/api/jobs", headers={"Authorization": f"bearer {jeton}"}).status_code == 200
          and lan.get("/api/jobs", headers={"Authorization": "Bearer " + "f" * 64}).status_code == 401
          and lan.get("/api/jobs", headers={"Authorization": jeton}).status_code == 401
          and lan.get("/api/jobs", headers={"Authorization": "Bearer " + jeton[:-1]}).status_code == 401)
    w = lan.post("/api/schedule", json={"title": "x", "run_at": "2026-10-04T09:00:00"}, headers=H)
    check("J3 DECISION #14 TENUE : meme avec un jeton, une ECRITURE depuis le reseau local est refusee (403)",
          w.status_code == 403 and "boucle locale" in w.text, f"{w.status_code} {w.text[:120]}")
    check("J4 les CLES restent interdites au reseau local, meme avec un jeton (_require_localhost intact)",
          lan.get("/api/settings/keys", headers=H).status_code == 403)
    check("J5 la liste des appareils et la rotation restent au PC, meme avec un jeton",
          lan.get("/api/devices", headers=H).status_code == 403 and lan.get("/api/devices/rotation", headers=H).status_code == 403)

    print("\n[R] revocation et rotation (depuis le PC)")
    ap = loc.get("/api/devices").json()
    ident = (ap.get("appareils") or [{}])[-1].get("id")
    check("R1 la liste (PC) : l'appareil, le maximum, et JAMAIS le jeton ni son empreinte",
          ap.get("max") == 5 and ident and jeton not in str(ap) and "jeton" not in str(ap), str(ap)[:200])
    check("R2 revoquer : 200, puis le jeton est refuse TOUT DE SUITE",
          loc.post(f"/api/devices/{ident}/revoke").status_code == 200 and lan.get("/api/jobs", headers=H).status_code == 401)
    check("R3 revoquer un inconnu ou deux fois : 404", loc.post(f"/api/devices/{ident}/revoke").status_code == 404
          and loc.post("/api/devices/nope/revoke").status_code == 404)
    rot = loc.get("/api/devices/rotation").json()
    check("R4 rotation : les consoles ou regenerer les cles", {"FAL_KEY", "TELEGRAM_BOT_TOKEN"} <= {c["cle"] for c in rot.get("consoles", [])})

    print("\n[C] ce qui ne bouge pas")
    csrf = loc.post("/api/schedule", json={"title": "x"}, headers={"Origin": "https://evil.example"})
    check("C1 la garde CSRF reste en place (Origin etranger : 403)", csrf.status_code == 403 and "Cross-origin" in csrf.text)
    ws = [r.path for r in app.routes if isinstance(r, WebSocketRoute)]
    check("C2 aucune route WebSocket (un middleware http ne les garde PAS : en ajouter une exige sa propre garde)", ws == [], str(ws))

print("\n[H] HOST jusqu'au lanceur")
from app.config import Settings                                    # noqa: E402
check("H1 le defaut reste la boucle locale", Settings.model_fields["HOST"].default == "127.0.0.1")
vbs = (_RACINE / "scripts" / "launch-silent.vbs").read_text(encoding="utf-8", errors="replace")
check("H2 le lanceur ne code plus l'hote en dur ; il passe LireHote(...) a uvicorn",
      "--host 127.0.0.1" not in vbs and '" -m uvicorn app.main:app --host " & hostArg & " --port 8765"' in vbs
      and "hostArg = LireHote(" in vbs)
i_f = vbs.find("Function LireHote(")
fonction = vbs[i_f:vbs.find("End Function", i_f) + len("End Function")] if i_f >= 0 else ""
cscript = shutil.which("cscript") or r"C:\Windows\System32\cscript.exe"
cas = {"absent": None, "ouvert": "HOST=0.0.0.0\n", "boucle": "HOST=127.0.0.1\n", "etranger": "HOST=10.0.0.9\n",
       "espaces": "FAL_KEY=x\n  HOST = 0.0.0.0  \n", "minuscule": "host=0.0.0.0\n", "commente": "# HOST=0.0.0.0\n",
       "dernier": "HOST=0.0.0.0\nHOST=127.0.0.1\n"}
lus = {}
if fonction and os.path.isfile(cscript):
    for k, contenu in cas.items():
        env = _tmp / f"env_{k}"
        if contenu is not None:
            env.write_bytes(contenu.replace("\n", "\r\n").encode("ascii"))
        h = _tmp / f"h_{k}.vbs"
        h.write_bytes(("Option Explicit\r\nDim fso, shell\r\nSet fso = CreateObject(\"Scripting.FileSystemObject\")\r\n"
                       "Set shell = CreateObject(\"WScript.Shell\")\r\n" + fonction.replace("\r\n", "\n").replace("\n", "\r\n")
                       + f"\r\nWScript.Echo LireHote(\"{env}\")\r\n").encode("cp1252", errors="replace"))
        p = subprocess.run([cscript, "//nologo", str(h)], capture_output=True, text=True, timeout=60)
        lus[k] = (p.stdout.strip() if p.returncode == 0 else f"ERREUR {p.returncode} {p.stderr.strip()[:80]}")
attendu = {"absent": "127.0.0.1", "ouvert": "0.0.0.0", "boucle": "127.0.0.1", "etranger": "127.0.0.1", "espaces": "0.0.0.0",
           "minuscule": "127.0.0.1", "commente": "127.0.0.1", "dernier": "127.0.0.1"}
check("H3 la VRAIE fonction du lanceur, executee par cscript sous Option Explicit : deux valeurs seulement, defaut boucle",
      lus == attendu, str(lus))
if os.path.isfile(cscript):
    # H5 : tout le lanceur doit se COMPILER — copie qui quitte juste apres Option Explicit : rien ne s'execute, aucun
    # backend ne demarre, mais une erreur de syntaxe n'importe ou dans le fichier fait echouer cscript.
    copie = _tmp / "lanceur_compile.vbs"
    copie.write_bytes(vbs.replace("Option Explicit", "Option Explicit\r\nWScript.Quit 0", 1).replace("\r\n", "\n")
                      .replace("\n", "\r\n").encode("cp1252", errors="replace"))
    pc = subprocess.run([cscript, "//nologo", str(copie)], capture_output=True, text=True, timeout=60)
    check("H5 le lanceur entier se compile (copie qui quitte avant toute action)", pc.returncode == 0, pc.stdout + pc.stderr)
    i_d = vbs.find("Function DataRoot(")
    fd = vbs[i_d:vbs.find("End Function", i_d) + len("End Function")] if i_d >= 0 else ""
    hd = _tmp / "h_dataroot.vbs"
    hd.write_bytes(("Option Explicit\r\nDim shell\r\nSet shell = CreateObject(\"WScript.Shell\")\r\n"
                    + fd.replace("\r\n", "\n").replace("\n", "\r\n") + "\r\nWScript.Echo DataRoot()\r\n").encode("cp1252"))
    e1 = dict(os.environ); e1.pop("DEEPOTUS_DATA_DIR", None)
    e2 = dict(os.environ); e2["DEEPOTUS_DATA_DIR"] = r"D:\donnees dz"
    d1 = subprocess.run([cscript, "//nologo", str(hd)], capture_output=True, text=True, env=e1, timeout=60).stdout.strip()
    d2 = subprocess.run([cscript, "//nologo", str(hd)], capture_output=True, text=True, env=e2, timeout=60).stdout.strip()
    check("H6 DataRoot = config._data_root : DEEPOTUS_DATA_DIR s'il est pose, sinon %LOCALAPPDATA%\\DeepotusVideoGenData",
          d1 == os.path.join(os.environ["LOCALAPPDATA"], "DeepotusVideoGenData") and d2 == r"D:\donnees dz", f"{d1} | {d2}")
dims = vbs[:vbs.find("Set fso")]
check("H4 Option Explicit : chaque variable du lanceur ajoutee est declaree (Dim hostArg)", "Option Explicit" in vbs and "hostArg" in dims, dims[-200:])

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
