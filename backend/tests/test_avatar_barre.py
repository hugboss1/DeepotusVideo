# -*- coding: utf-8 -*-
"""Avatar live G7 (t168, 10/10/2026) — l'entrée « Avatar live » de la barre des applications : maillon de queue
scripts/patch_bundle_avatar.py, posé sur le bundle versionné. Vérifié DANS le bundle livré : l'entrée de rail (icône
Glyph, description traduite), la vue iframe /avatar/ qui reçoit caméra et micro (sinon le Direct ne peut pas ouvrir la
webcam dans l'application), la navigation ?view=avatarlive ; l'inverse `avant_avatar` défait le maillon à l'octet ; une
double application est refusée ; le serveur sert la page /avatar/.
Run (depuis backend/) : & $PY tests/test_avatar_barre.py"""
import os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzavbarre_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parents[1]
sys.path.insert(0, str(_ICI.parent)); sys.path.insert(0, str(_ICI)); sys.path.insert(0, str(RACINE / "scripts"))
from loguru import logger                                           # noqa: E402
logger.remove()
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


import patch_bundle_avatar as M                                     # noqa: E402
import _i18n_l1_aide as A                                           # noqa: E402
B = (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes().decode("utf-8")

print("\n[B] le bundle livré")
check("B1 le marqueur du maillon une seule fois", B.count(M.MARKER) == 1, str(B.count(M.MARKER)))
check("B2 l'entrée de rail : après le Photolab, icône Glyph dz-media-avatar, description par dzT(avatar.rail.desc)",
      '"pplab"' in B and 'dzT("coque.rail.photolab_desc"),new:!0},{id:"avatarlive",label:"Avatar live",icon:"dz-media-avatar",'
      'desc:dzT("avatar.rail.desc"),new:!0}' in B)
check("B3 la vue : une iframe /avatar/ qui reçoit caméra ET micro (allow), clé pavlive",
      's==="avatarlive"&&r.jsx("iframe",{src:"/avatar/",title:"Avatar live",allow:"camera; microphone; autoplay",' in B
      and '"pavlive"' in B)
check("B4 ?view=avatarlive ouvre l'écran (liste blanche des vues navigables)", '"photolab","avatarlive"],sg=Yu.includes(' in B)
check("B5 aucun .bak_avatar laissé (il deviendrait un faux maillon de la chaîne)",
      not (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js.bak_avatar").exists())
r = subprocess.run(["node", "--check", str(RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js")], capture_output=True)
check("B6 le bundle reste du JavaScript valide (node --check)", r.returncode == 0, r.stderr.decode("utf-8", "replace")[-200:])
dico = (RACINE / "frontend" / "shared" / "dz-i18n-dico.js").read_text(encoding="utf-8")
check("B7 la description est au dictionnaire en FR et EN", '"avatar.rail.desc": {"fr": "Personnages, Recast et Direct", "en": "Characters, Recast and Live"}' in dico)

print("\n[I] l'inverse (bancs de traduction)")
sans = A.avant_avatar(B)
check("I1 avant_avatar défait les trois paires : plus de marqueur, plus d'iframe /avatar/",
      M.MARKER not in sans and 'src:"/avatar/"' not in sans and '"photolab"],sg=Yu.includes(' in sans)
check("I2 l'aller-retour est exact à l'octet (réappliquer les paires rend le bundle d'avant les nœuds t168b, posés après)",
      M.appliquer(sans) == A.avant_avnoeuds(B))
check("I3 avant_dzsched défait D'ABORD l'entrée Avatar live (posée après lui)",
      M.MARKER not in A.avant_dzsched(B) and '"data-dz-debord":"1"' not in A.avant_dzsched(B))
check("I4 un bundle sans le maillon passe tel quel", A.avant_avatar(sans) == sans)
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_avatar.py"), "--check"], capture_output=True,
                   text=True, cwd=str(RACINE))
check("I5 le maillon refuse une double application (--check sur le bundle livré)", r.returncode != 0 and "double application" in (r.stdout + r.stderr), r.stdout + r.stderr)

print("\n[S] le serveur sert la page")
from fastapi.testclient import TestClient                           # noqa: E402
from app.main import app                                            # noqa: E402
with TestClient(app, client=("127.0.0.1", 5), follow_redirects=False) as c:
    r = c.get("/avatar/")
    check("S1 /avatar/ : la page Avatar live, sans cache", r.status_code == 200 and "<title>Avatar live</title>" in r.text
          and "no-cache" in r.headers.get("cache-control", ""), str(r.status_code))
    r = c.get("/avatar")
    check("S2 /avatar sans barre finale : redirigé vers /avatar/ (pas le catch-all de l'application)",
          r.status_code == 307 and r.headers.get("location") == "/avatar/", str(r.status_code))
    check("S3 le module du SDK et ses licences sont servis", c.get("/avatar/vendor/decart-sdk-0.2.8.js").status_code == 200
          and c.get("/avatar/vendor/LICENCES.txt").status_code == 200)

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
