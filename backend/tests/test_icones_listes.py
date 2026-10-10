# -*- coding: utf-8 -*-
"""Icônes, listes déroulantes (10/10/2026) — plus aucun glyphe ni emoji collé dans une <option>.

Une <option> native ne peut pas porter d'icône dessinée : l'origine d'un élément est dite par un groupe <optgroup>.
  [1] Plateau 3D, menu des maillages : les entités de la bible sous « Entités de la bible », les maillages des jobs
      sous « Maillages 3D » ; le ◆ est retiré (et la lecture du nom ne le retire plus).
  [2] Studio 3D, photos des vues : celles du téléphone groupées en tête sous « Téléphone » (comportement exécuté :
      test_studio3d_photos U1) ; la légende porte l'icône dz-etat-mobile au lieu du 📱.
Run : & $PY tests/test_icones_listes.py   (depuis backend/)
"""
import pathlib, re, shutil, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}  {str(detail)[:300]}")


def code(rel):
    """Le fichier sans ses commentaires /* … */ et // … (les commentaires peuvent citer les anciens glyphes)."""
    t = (ROOT / rel).read_text(encoding="utf-8")
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$", "", t)


print("[1] Plateau 3D")
pl = code("frontend/plateau/plateau.js")
check("1.1 entités de la bible sous un <optgroup> « Entités de la bible »", '<optgroup label="Entités de la bible">' in pl)
check("1.2 maillages des jobs sous « Maillages 3D »", '<optgroup label="Maillages 3D">' in pl)
check("1.3 plus aucun ◆ dans le code du Plateau", "◆" not in pl, pl.count("◆"))
check("1.4 le nom posé dans la scène reste « Nom (bible) »", "l: `${e.nom} (bible)`" in pl)

print("[2] Studio 3D")
vu = code("frontend/studio3d/vues.js")
ix = (ROOT / "frontend/studio3d/index.html").read_text(encoding="utf-8")
check("2.1 photos du téléphone sous <optgroup> « Téléphone », le reste sous « Bibliothèque »",
      '<optgroup label="Téléphone">' in vu and '<optgroup label="Bibliothèque">' in vu)
check("2.2 plus aucun 📱 dans les listes ni dans la légende", "📱" not in vu and "📱" not in ix)
check("2.3 la légende porte l'icône dz-etat-mobile", ix.count('dz-icons.svg#dz-etat-mobile') == 1)

print("[3] syntaxe")
node = shutil.which("node")
for f in ("frontend/plateau/plateau.js", "frontend/studio3d/vues.js"):
    r = subprocess.run([node, "--check", str(ROOT / f)], capture_output=True, text=True) if node else None
    check(f"3.x node --check {f}", r is not None and r.returncode == 0, r.stderr[-200:] if r else "node absent")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
