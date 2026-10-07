"""Spike de latence du Photolab (t136, décision D1) : combien coûte un aller-retour moteur sur une image 1920 × 1080 ?
Ouvre une image synthétique dans photocraft-cli serve, puis mesure (médiane de 5) : doc.render maxSide 1024 et 1920,
filtre flou gaussien r=3, niveaux, nouveau calque + remplissage, et l'aller-retour complet « commande + rendu 1920 ».
Usage : python scripts/photolab_mesure.py     (le binaire doit être fourni : scripts/vendor_photocraft.py)
"""
import os, pathlib, statistics, sys, tempfile, time

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "backend"))
d = pathlib.Path(tempfile.mkdtemp(prefix="dzmesure_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(d)
from PIL import Image                                          # noqa: E402
from app.services import photolab_moteur as PM                # noqa: E402

w = PM.dossier_travail()
img = Image.effect_mandelbrot((1920, 1080), (-2.2, -1.2, 1.0, 1.2), 100).convert("RGB")
img.save(w / "entrees" / "m.png")
s = PM.SessionMoteur([str(PM.chemin_cli()), "serve", "--automation-read-root", str(w), "--automation-write-root", str(w)],
                     delai_s=120)
s.appeler("doc.open", {"path": "entrees/m.png"})


def mesure(nom, f, n=5):
    t = []
    for _ in range(n):
        t0 = time.perf_counter()
        f()
        t.append((time.perf_counter() - t0) * 1000)
    print(f"| {nom} | {statistics.median(t):.0f} ms | {min(t):.0f}–{max(t):.0f} ms |")


print("| Mesure (1920 × 1080, médiane de 5) | Médiane | Écart |\n|---|---|---|")
mesure("doc.render maxSide 1024", lambda: s.appeler("doc.render", {"path": "rendus/a.png", "maxSide": 1024}))
mesure("doc.render maxSide 1920", lambda: s.appeler("doc.render", {"path": "rendus/a.png", "maxSide": 1920}))
mesure("flou gaussien r=3", lambda: s.appeler("engine.execute", {"command": "filter.blur.gaussianBlur", "params": {"radius": 3}}))
mesure("niveaux", lambda: s.appeler("engine.execute", {"command": "image.adjustments.levels",
                                                       "params": {"lightness": {"outBlack": 20}}}))
mesure("nouveau calque + remplissage", lambda: (s.appeler("engine.execute", {"command": "layer.new.layer", "params": {}}),
                                               s.appeler("engine.execute", {"command": "edit.fill", "params": {"color": "#336699"}})))
mesure("aller-retour flou + rendu 1920", lambda: (s.appeler("engine.execute", {"command": "filter.blur.gaussianBlur",
                                                                                  "params": {"radius": 1}}),
                                                 s.appeler("doc.render", {"path": "rendus/a.png", "maxSide": 1920})))
s.fermer()
