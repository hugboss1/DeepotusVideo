# -*- coding: utf-8 -*-
"""Planificateur (10/10/2026) — l'écran ne déborde plus de la fenêtre.

Mesure d'origine à 1 600 × 1 000 : <main> à 1 645 px pour 1 368 disponibles (en-tête et panneau de droite coupés),
parce que la grille `1fr 420px` ne descendait pas sous la largeur de la barre d'outils `Dm` qui ne passait jamais à
la ligne. Après le maillon scripts/patch_bundle_dzsched.py, mesuré au navigateur : <main> = 1 368 px à 1 600,
1 134 à 1 366, 1 048 à 1 280, aucun élément au-delà du bord, en vue Semaine comme en vue Mois.

  [1] le maillon est posé une fois : marqueur, piste `minmax(0,1fr) 420px`, colonne `minWidth:0`, barre `Dm` en
      `flexWrap:"wrap"` ; l'ancienne piste `1fr 420px` a disparu.
  [2] la chaîne reste saine : bundle `node --check`, CRLF homogène (octets), aucun `.bak_dzsched` laissé (il serait
      pris pour un maillon par repatch_all), le maillon refuse une double application, `version` sondé intact.
Run : & $PY tests/test_scheduler_debordement.py   (depuis backend/)
"""
import pathlib, shutil, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
PATCHER = ROOT / "scripts" / "patch_bundle_dzsched.py"
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}  {str(detail)[:300]}")


raw = BUNDLE.read_bytes()
s = raw.decode("utf-8-sig")
print("[1] le maillon")
check("1.1 marqueur posé une fois", s.count('"data-dz-debord":"1"') == 1, s.count('"data-dz-debord":"1"'))
check("1.2 piste de gauche minmax(0,1fr), plus de « 1fr 420px »",
      s.count('gridTemplateColumns:"minmax(0,1fr) 420px"') == 1 and 'gridTemplateColumns:"1fr 420px"' not in s)
check("1.3 colonne de gauche minWidth:0 (devant la barre Dm)",
      s.count('{display:"flex",flexDirection:"column",minHeight:0,minWidth:0},children:[r.jsx(Dm,') == 1)
i = s.find("function Dm(")
check("1.4 la barre d'outils Dm passe à la ligne", i > 0 and 'gap:12,flexWrap:"wrap",rowGap:8}' in s[i:i + 400])

print("[2] la chaîne")
node = shutil.which("node")
r = subprocess.run([node, "--check", str(BUNDLE)], capture_output=True, text=True) if node else None
check("2.1 bundle node --check", r is not None and r.returncode == 0, r.stderr[-300:] if r else "node absent")
check("2.2 CRLF homogène (octets)", raw.count(b"\r\n") > 15000 and raw.count(b"\n") == raw.count(b"\r\n"))
check("2.3 aucun .bak_dzsched laissé", not (BUNDLE.parent / (BUNDLE.name + ".bak_dzsched")).exists())
r = subprocess.run([sys.executable, str(PATCHER), "--check"], capture_output=True, text=True, cwd=str(ROOT))
check("2.4 double application refusée", r.returncode != 0 and "deja present" in (r.stdout + r.stderr), r.stdout + r.stderr)
src = PATCHER.read_text(encoding="utf-8")
check("2.5 le maillon lit le bundle en octets", "read_bytes()" in src and "read_text(" not in src.split('"""', 2)[2])
check("2.6 version intact (v2.8.0 x4)", s.count("v2.8.0") == 4, s.count("v2.8.0"))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
