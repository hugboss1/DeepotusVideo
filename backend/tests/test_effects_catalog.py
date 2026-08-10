# -*- coding: utf-8 -*-
"""Catalogue d'effets + route d'apercu.

Ce que ce fichier verifie :
  [1] chaque effet du catalogue produit une chaine de filtres VALIDE — pas
      « structurellement plausible » : ffmpeg la rend pour de vrai ;
  [2] chaque categorie declaree est non vide et chaque effet en a une ;
  [3] chaque parametre declare a des bornes exploitables ;
  [4] la route d'apercu refuse un type inconnu et une source hors dossier,
      et met bien en cache.
"""
import os
import subprocess
import sys
import tempfile

os.environ.setdefault("DEEPOTUS_DATA_DIR", tempfile.mkdtemp(prefix="dzfxcat_"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _ffmpeg():
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    cand = os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
    if os.path.isfile(cand):
        return cand
    print("SKIP: ffmpeg introuvable")
    sys.exit(0)


FF = _ffmpeg()

from app.services import effects_engine as fx          # noqa: E402
from app.services import effects_preview as fxp        # noqa: E402
from app.config import settings                        # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


cat = fx.catalog()
cats = fx.categories()

print(f"\n[1] Chaine ffmpeg valide pour les {len(cat)} effets du catalogue")
tmp = tempfile.mkdtemp(prefix="dzfxcat_out_")
src = os.path.join(tmp, "src.png")
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi",
                "-i", "testsrc2=size=320x180", "-frames:v", "1", "-update", "1", src],
               check=True, timeout=60)

bad = []
for name in sorted(cat):
    spec = cat[name]
    eff = {"type": name}
    for p in spec.get("params") or []:
        b = spec["bounds"][p]
        eff[p] = 75 if p == "intensity" else b.get("default")
    chain = fx.build_chain([eff], "0:v", "vout", "u1",
                           {"w": 320, "h": 180, "dur": 2.0, "fps": 25})
    out = os.path.join(tmp, f"{name}.mp4")
    r = subprocess.run([FF, "-y", "-v", "error", "-loop", "1", "-framerate", "25",
                        "-t", "1.2", "-i", src, "-filter_complex", ";".join(chain),
                        "-map", "[vout]", "-pix_fmt", "yuv420p", out],
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
        last = (r.stderr or "").strip().splitlines()
        bad.append((name, last[-1][:160] if last else "sortie vide"))
print(f"  {len(cat) - len(bad)}/{len(cat)} effets rendus")
for n, why in bad:
    print(f"    - {n}: {why}")
check("aucun effet du catalogue ne casse le filtergraph", not bad)
check("chaque effet du catalogue existe dans EFFECTS",
      all(n in fx.EFFECTS for n in cat),
      str([n for n in cat if n not in fx.EFFECTS]))

print("\n[2] Categories")
ids = [c["id"] for c in cats]
check("categories declarees", len(ids) >= 6, str(ids))
vides = [c["id"] for c in cats if c["count"] == 0]
check("aucune categorie vide", not vides, str(vides))
orphelins = [n for n, s in cat.items() if s.get("cat") not in ids]
check("chaque effet porte une categorie connue", not orphelins, str(orphelins))
reels = {}
for n, s in cat.items():
    reels[s["cat"]] = reels.get(s["cat"], 0) + 1
for c in cats:
    print(f"    {c['id']:12s} {c['label']:14s} {reels.get(c['id'], 0)} effets")

print("\n[3] Bornes des parametres")
mauvais = []
for n, s in cat.items():
    for p in s.get("params") or []:
        b = (s.get("bounds") or {}).get(p)
        if not b or "type" not in b or "default" not in b:
            mauvais.append(f"{n}.{p}")
        elif b["type"] == "range" and not (b["min"] < b["max"]):
            mauvais.append(f"{n}.{p} (bornes)")
        elif b["type"] == "choice" and not b.get("choices"):
            mauvais.append(f"{n}.{p} (choix vides)")
check("chaque parametre a des bornes utilisables", not mauvais, str(mauvais))
check("libelle FR sur chaque effet",
      all(s.get("label") and s.get("hint") for s in cat.values()))

print("\n[4] Garde-fous de la route d'apercu")
try:
    fxp.render_preview("movie=C\\:/Windows/win.ini", {})
    check("type inconnu refuse", False, "aucune exception")
except ValueError as e:
    check("type inconnu refuse", True)
    print(f"    -> ValueError: {e}")
except Exception as e:                                   # noqa: BLE001
    check("type inconnu refuse", False, repr(e))

for hostile in ("image:../../deepotus.db", "image:C:/Windows/win.ini",
                "image:..\\.env", "fichier:/etc/passwd"):
    try:
        fxp.render_preview("blur", {}, source=hostile)
        check(f"source refusee : {hostile}", False, "aucune exception")
    except ValueError:
        check(f"source refusee : {hostile}", True)
    except Exception as e:                               # noqa: BLE001
        check(f"source refusee : {hostile}", False, repr(e))

# Une image REELLE de la bibliotheque doit, elle, passer.
lib = settings.images_path / "dz_test_fx.png"
subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=160x90",
                "-frames:v", "1", "-update", "1", str(lib)], check=True, timeout=60)
try:
    p = fxp.render_preview("vignette", {"intensity": 80}, source=f"image:{lib.name}")
    check("image de la bibliotheque acceptee", p.is_file() and p.stat().st_size > 0)
except Exception as e:                                   # noqa: BLE001
    check("image de la bibliotheque acceptee", False, repr(e))

print("\n[5] Coercition des parametres et cache")
c = fxp.coerce_params("lightleak", {"intensity": 999, "angle": -40,
                                    "c0": "javascript:alert(1)", "inconnu": "x'; rm -rf",
                                    "file": "../../evil.cube"})
check("intensite ramenee dans les bornes", c.get("intensity") == 100, str(c))
check("angle ramene dans les bornes", c.get("angle") == 0, str(c))
check("couleur invalide rejetee", "c0" not in c, str(c))
check("parametre non declare ignore", "inconnu" not in c and "file" not in c, str(c))

a = fxp.render_preview("swirl", {"intensity": 60})
m1 = a.stat().st_mtime_ns
b = fxp.render_preview("swirl", {"intensity": 60})
check("meme combinaison = meme fichier de cache", a == b)
check("cache non regenere (ffmpeg non relance)", b.stat().st_mtime_ns == m1)
d = fxp.render_preview("swirl", {"intensity": 61})
check("parametre different = autre entree de cache", d != a)

payload = fxp.catalog_payload()
check("catalog_payload complet",
      bool(payload.get("categories")) and len(payload.get("effects") or {}) == len(cat))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
