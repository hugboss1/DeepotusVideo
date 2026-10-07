# -*- coding: utf-8 -*-
"""t136 (Photolab P1) — FIDÉLITÉ (décision D1) avec le VRAI moteur : pour chaque commande, notre pont
(/api/photolab : ouvrir -> executer -> enregistrer png) et `photocraft-cli run <entrée> --cmd … --out` donnent les
MÊMES pixels. Rouge si le binaire manque (lancer `python scripts/vendor_photocraft.py`) : jamais un faux vert.
Run : & $PY tests/test_photolab_fidelite.py   (depuis backend/)"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt136f_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
from PIL import Image, ImageDraw                              # noqa: E402
from app.services import photolab_moteur as PM                # noqa: E402
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:300]}")


try:
    CLI = PM.chemin_cli()
except PM.MoteurAbsent as e:
    check("0 le vrai moteur est fourni", False, e)
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)

# une entrée déterministe : dégradé, formes, couleurs saturées (un flou ou des niveaux y changent des pixels)
im = Image.new("RGB", (96, 64))
px = im.load()
for y in range(64):
    for x in range(96):
        px[x, y] = (x * 255 // 95, y * 255 // 63, (x * y) % 256)
dr = ImageDraw.Draw(im)
dr.rectangle((10, 10, 40, 30), fill=(250, 20, 20))
dr.ellipse((50, 20, 90, 60), fill=(20, 200, 60))
im.save(_tmp / "images" / "entree.png")

CAS = [("filter.blur.gaussianBlur", {"radius": 3}), ("image.adjustments.invert", {}),
       ("image.adjustments.levels", {"lightness": {"outBlack": 60}}), ("image.adjustments.equalize", {}),
       ("filter.blur.average", {})]


def reference(cid, params, sortie):
    r = subprocess.run([str(CLI), "run", str(_tmp / "images" / "entree.png"), "--cmd", cid, "--params", json.dumps(params),
                        "--out", str(sortie)], capture_output=True, text=True, timeout=120)
    return r.returncode == 0 and sortie.is_file(), r.stderr[-300:]


def pixels(p):
    # tobytes plutôt que getdata (retiré dans Pillow 14) ; taille en tête : deux images de tailles différentes
    # dont les octets coïncideraient ne passent pas pour égales.
    with Image.open(p) as i:
        o = i.convert("RGBA").tobytes()
        return [i.size] + [o[k:k + 4] for k in range(0, len(o), 4)]


async def scenario():
    import httpx
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t",
                                 timeout=120) as c:
        for cid, params in CAS:
            ref = _tmp / f"ref-{cid}.png"
            fait, err = reference(cid, params, ref)
            if not fait:
                check(f"{cid} : référence photocraft-cli run", False, err)
                continue
            r1 = await c.post("/api/photolab/ouvrir", json={"filename": "entree.png"})
            r2 = await c.post("/api/photolab/executer", json={"command": cid, "params": params})
            r3 = await c.post("/api/photolab/enregistrer", json={"format": "png", "nom": f"pont-{cid.replace('.', '-')}"})
            if not (r1.status_code == r2.status_code == r3.status_code == 200):
                check(f"{cid} : le pont répond", False, (r1.text, r2.text, r3.text))
                PM.fermer()
                continue
            # le nom RENDU par la route (elle n'écrase jamais : -2, -3… si le nom est pris)
            pont = PM.dossier_travail() / "exports" / r3.json()["fichier"]
            a, b = pixels(ref), pixels(pont)
            check(f"{cid} {params} : mêmes pixels que photocraft-cli", a == b and pixels(_tmp / "images" / "entree.png") != a,
                  f"{sum(x != y for x, y in zip(a, b))} pixels différents, tailles {len(a)}/{len(b)}")
            PM.fermer()                                   # un moteur neuf par cas : aucun document d'un cas ne reste
    PM.fermer()

asyncio.run(scenario())
print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
