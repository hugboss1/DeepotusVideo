# -*- coding: utf-8 -*-
"""Garde serveur de POST /api/images/upload (01/10/2026, trouvé pendant la preuve écran des zones de dépôt Quick,
tâche #54 T9) : la route écrivait N'IMPORTE QUEL fichier dans la Bibliothèque (un `note.txt` répondait 200
« importée ») et écrasait en silence un fichier homonyme.
Désormais : le contenu est DÉCODÉ par Pillow ; tout ce qui n'est pas PNG/JPEG/WebP/GIF/BMP/AVIF est refusé en 415
avec un détail français qui nomme l'extension et le format reçus (miroir de /videos/upload, « vide ou illisible »).
Écrasement : un nom homonyme reçoit `nom-1.ext` (renvoyé dans `filename`) — SAUF les exports `vector_` du Vectorlab,
dont le nom STABLE est un contrat (Cardforge mod-face.js `vecExportNom` reconstruit `vector_<id>_2x.png` sans lire
la réponse : « re-exporter RÉÉCRIT le fichier en place, la carte suit le vecteur »).
Témoin positif : la route de la base (4196b70a), exécutée telle quelle, accepte un .txt.
Data-dir isolé, aucun réseau. Run (depuis backend/) : & $PY tests/test_images_upload_garde.py"""
import ast, io, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzimgup_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
_DB = _tmp / "t.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB.as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
_IMG = _tmp / "images"
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()
from PIL import Image                                               # noqa: E402
from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile  # noqa: E402
from fastapi.testclient import TestClient                           # noqa: E402
from app.config import settings                                     # noqa: E402
from app.main import app                                            # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _image(fmt, couleur=(200, 30, 60)):
    b = io.BytesIO()
    mode = "RGB" if fmt in ("JPEG", "BMP", "AVIF") else "RGBA"
    Image.new(mode, (24, 16), couleur if mode == "RGB" else couleur + (255,)).save(b, fmt)
    return b.getvalue()


def _up(c, nom, data, mime="application/octet-stream"):
    return c.post("/api/images/upload", files={"file": (nom, data, mime)})


PNG = _image("PNG")
TXT = "note de réunion — pas une image\n".encode("utf-8")

# ── témoin : la route de la base, extraite et exécutée telle quelle, accepte un .txt ──
BASE = "4196b70a"
print("[T] témoin de la base")
src = subprocess.run(["git", "show", f"{BASE}:backend/app/api/routes.py"], capture_output=True, cwd=str(_ICI.parent))
fn = None
if src.returncode == 0:
    texte = src.stdout.decode("utf-8")
    for n in ast.parse(texte).body:
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "upload_image":
            fn = n
check("T1 la base porte la fonction upload_image", fn is not None)
if fn is not None:
    lignes = texte.splitlines()
    code = "\n".join(lignes[fn.decorator_list[0].lineno - 1:fn.end_lineno])

    class _LI:
        notes = []
        @staticmethod
        async def noter(files, source, **kw):
            _LI.notes.append((list(files), source))

    vieux_dir = _tmp / "vieux"
    vieux_dir.mkdir()
    class _S:
        images_path = vieux_dir
    ns = {"router": APIRouter(), "settings": _S, "Path": pathlib.Path, "File": File, "UploadFile": UploadFile,
          "HTTPException": HTTPException, "LI": _LI}
    exec(compile(code, "base_upload_image", "exec"), ns)
    vieux = FastAPI()
    vieux.include_router(ns["router"], prefix="/api")
    with TestClient(vieux, client=("127.0.0.1", 50000)) as cv:
        r = _up(cv, "note.txt", TXT, "text/plain")
        check("T2 la base répond 200 à note.txt", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
        check("T3 la base a ÉCRIT note.txt dans la Bibliothèque", (vieux_dir / "note.txt").read_bytes() == TXT)
        _up(cv, "photo.png", PNG, "image/png")
        r2 = _up(cv, "photo.png", _image("PNG", (1, 2, 3)), "image/png")
        check("T4 la base ÉCRASE photo.png en silence (même filename rendu)",
              r2.json().get("filename") == "photo.png" and (vieux_dir / "photo.png").read_bytes() != PNG)

check("T5 l'application de test écrit bien dans le data-dir isolé", settings.images_path.resolve() == _IMG.resolve(),
      str(settings.images_path))


def _fichiers():
    return sorted(p.name for p in _IMG.iterdir())


with TestClient(app, client=("127.0.0.1", 50000)) as c:
    print("\n[A] refus : tout ce qui n'est pas une image")
    avant = _fichiers()
    r = _up(c, "note.txt", TXT, "text/plain")
    d = r.json().get("detail", "") if r.headers.get("content-type", "").startswith("application/json") else ""
    check("A1 note.txt → 415", r.status_code == 415, f"{r.status_code} {r.text[:200]}")
    check("A2 le détail est français et nomme l'extension reçue",
          "pas une image" in d.lower() and "« .txt »" in d and "note.txt" in d, d)
    check("A3 le détail dit les formats acceptés", all(f in d for f in ("PNG", "JPEG", "WebP", "GIF", "BMP", "AVIF")), d)
    check("A4 rien n'est écrit dans la Bibliothèque", _fichiers() == avant, str(_fichiers()))

    r = _up(c, "faux.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image/png")
    d = r.json().get("detail", "")
    check("A5 un faux PNG (signature seule) → 415 nommant « .png »", r.status_code == 415 and "« .png »" in d, f"{r.status_code} {d}")
    check("A6 rien n'est écrit", "faux.png" not in _fichiers())

    tronque = PNG[:len(PNG) // 2]
    r = _up(c, "coupe.png", tronque, "image/png")
    check("A7 un PNG tronqué → 415", r.status_code == 415, f"{r.status_code} {r.text[:200]}")

    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10"/></svg>'
    r = _up(c, "logo.svg", svg, "image/svg+xml")
    d = r.json().get("detail", "")
    check("A8 un SVG → 415 nommant « .svg » (le Vectorlab n'en dépose jamais ici)", r.status_code == 415 and "« .svg »" in d, f"{r.status_code} {d}")

    r = _up(c, "vide.png", b"", "image/png")
    check("A9 un fichier vide → 415", r.status_code == 415, f"{r.status_code} {r.text[:200]}")

    r = _up(c, "scan.tif", _image("TIFF"), "image/tiff")
    d = r.json().get("detail", "")
    check("A10 un TIFF (décodable mais hors liste) → 415 nommant le format TIFF", r.status_code == 415 and "TIFF" in d, f"{r.status_code} {d}")

    r = _up(c, "image.png.txt", PNG, "text/plain")
    check("A11 c'est le CONTENU qui décide : un vrai PNG mal nommé passe (200)", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

    r = _up(c, "..", PNG, "image/png")
    check("A12 nom invalide : toujours 400 (garde de nom intacte)", r.status_code in (400, 422), f"{r.status_code}")
    check("A13 aucun fichier refusé n'a laissé de trace", not any(n in _fichiers() for n in
          ("note.txt", "faux.png", "coupe.png", "logo.svg", "vide.png", "scan.tif")), str(_fichiers()))

    print("\n[B] acceptés : PNG, JPEG, WebP, GIF, BMP, AVIF")
    for fmt, ext in (("PNG", "png"), ("JPEG", "jpg"), ("WEBP", "webp"), ("GIF", "gif"), ("BMP", "bmp"), ("AVIF", "avif")):
        data = _image(fmt)
        r = _up(c, f"ok_{fmt.lower()}.{ext}", data, f"image/{ext}")
        nom = r.json().get("filename") if r.status_code == 200 else None
        check(f"B {fmt} → 200 et octets identiques sur disque",
              nom is not None and (_IMG / nom).read_bytes() == data, f"{r.status_code} {r.text[:200]}")

    print("\n[C] homonyme : nom-1.ext, l'original intact")
    p1 = _image("PNG", (10, 10, 10)); p2 = _image("PNG", (20, 20, 20)); p3 = _image("PNG", (30, 30, 30))
    r1 = _up(c, "photo.png", p1, "image/png")
    r2 = _up(c, "photo.png", p2, "image/png")
    r3 = _up(c, "photo.png", p3, "image/png")
    check("C1 premier dépôt garde son nom", r1.json().get("filename") == "photo.png", r1.text[:200])
    check("C2 deuxième dépôt → photo-1.png rendu dans filename", r2.json().get("filename") == "photo-1.png", r2.text[:200])
    check("C3 troisième dépôt → photo-2.png", r3.json().get("filename") == "photo-2.png", r3.text[:200])
    check("C4 l'original n'est PAS écrasé", (_IMG / "photo.png").read_bytes() == p1)
    def _lire(nom):
        f = _IMG / nom
        return f.read_bytes() if f.is_file() else None
    check("C5 chaque fichier porte ses octets", _lire("photo-1.png") == p2 and _lire("photo-2.png") == p3)
    check("C6 `saved` désigne le fichier réellement écrit",
          pathlib.Path(r2.json().get("saved", "")).name == "photo-1.png", r2.text[:200])

    print("\n[D] export Vectorlab : le nom stable vector_ est réécrit en place")
    v1 = _image("PNG", (40, 40, 40)); v2 = _image("PNG", (50, 50, 50))
    a = _up(c, "vector_doc7_2x.png", v1, "image/png")
    b = _up(c, "vector_doc7_2x.png", v2, "image/png")
    check("D1 même filename rendu deux fois", a.json().get("filename") == b.json().get("filename") == "vector_doc7_2x.png",
          f"{a.text[:120]} | {b.text[:120]}")
    check("D2 le fichier porte la DERNIÈRE version (la carte suit le vecteur)", _lire("vector_doc7_2x.png") == v2)
    check("D3 aucun vector_doc7_2x-1.png", "vector_doc7_2x-1.png" not in _fichiers())
    r = _up(c, "vector_doc7_2x.png", TXT, "text/plain")
    check("D4 la garde de contenu vaut aussi pour vector_ (415, l'export précédent intact)",
          r.status_code == 415 and _lire("vector_doc7_2x.png") == v2, f"{r.status_code}")

    print("\n[E] provenance : l'index note le nom RÉELLEMENT écrit")
    li = {i["filename"]: i for i in c.get("/api/images").json()["images"]}
    check("E1 photo-1.png indexé « import » au dépôt",
          li.get("photo-1.png", {}).get("source") == "import" and li["photo-1.png"].get("source_origin") == "depot",
          str(li.get("photo-1.png")))
    check("E2 vector_doc7_2x.png indexé « vectorlab »", li.get("vector_doc7_2x.png", {}).get("source") == "vectorlab",
          str(li.get("vector_doc7_2x.png")))

print(f"\n{ok} ok, {fail} échec(s)")
sys.exit(1 if fail else 0)
