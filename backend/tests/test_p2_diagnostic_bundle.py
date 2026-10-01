# -*- coding: utf-8 -*-
"""Tache #15 (plan Settings T3, 29/09/2026) — L'ECRAN DIAGNOSTIC DES REGLAGES dans le bundle (sections P2dg1..P2dg4,
groupe P1 du maillon montage). Temoin : le bundle de la base (git show) n'a ni l'entree, ni la section, ni la
branche. Le banc relit le BUNDLE LIVRE : ancres consommees, entree en tete de la barre ET dans la liste blanche `ym`
(sans elle ?section=diag retombe sur accounts), branche du corps, fins de ligne intactes ; dzOct executee sous node.
Run : & $PY tests/test_p2_diagnostic_bundle.py   (depuis backend/)"""
import json, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "scripts"))
import patch_bundle_montage as P                              # noqa: E402

BASE = "e113a08"
NODE = shutil.which("node")
BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.with_name(BUNDLE.name + ".bak_montage")
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:500]
    except Exception as e:                                    # pragma: no cover
        return f"(detail illisible : {e})"


raw = BUNDLE.read_bytes()
s = raw.decode("utf-8")
bak = BAK.read_bytes().decode("utf-8") if BAK.is_file() else ""
vieux = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], cwd=ROOT, capture_output=True).stdout.decode("utf-8")
SEC = {t: (a, r) for t, a, r in P.PATCHES if t.startswith("P2dg")}

print("\n[0] temoin : le bundle de la base (%s)" % BASE)
check("0.1 TEMOIN : ni DzDiag, ni entree « Diagnostic », ni 'diag' dans ym, ni branche",
      vieux.count("function DzDiag(") == 0 and vieux.count('{k:"diag"') == 0 and vieux.count('const ym=["diag"') == 0
      and vieux.count('s==="diag"') == 0 and vieux.count('const ym=["keys",') == 1, "")

print("\n[1] les quatre sections")
check("1.1 quatre sections P2dg, en QUEUE de PATCHES", list(SEC) == ["P2dg1-bloc-dzdiag-avant-dzpricing", "P2dg2-entree-diagnostic-de-la-barre",
      "P2dg3-diag-dans-la-liste-blanche-ym", "P2dg4-branche-diag-du-corps"] and [t for t, _a, _r in P.PATCHES][[t for t, _a, _r in P.PATCHES].index(list(SEC)[0]):][:4] == list(SEC)
      and all(t.startswith(("P2pl", "P2cl", "P2rc", "P3", "P5")) for t in   # + P5qr (tache #48, 01/10)
           [t for t, _a, _r in P.PATCHES][[t for t, _a, _r in P.PATCHES].index(list(SEC)[0]) + 4:]),
      _d(list(SEC)))  # #22 : + P2rc1 ; #31 : repéré par position, + le lot P3
for t, (a, r) in SEC.items():
    garde = r.endswith(a[1:]) if t.startswith("P2dg1") else True
    check(f"1.x {t} : ancre x1 dans .bak_montage, touchee par aucune autre section, remplacement x1 livre",
          bak.count(a) == 1 and sum(1 for t2, a2, r2 in P.PATCHES if t2 != t and (a in a2 or a in r2)) == 0
          and s.count(r) == 1 and garde and "\n" not in r and "\r" not in r, _d(bak.count(a), s.count(r)))

print("\n[2] l'ecran dans le bundle livre")
check("2.1 « Diagnostic » en TETE de la barre laterale", s.count('[{k:"diag",l:"Diagnostic"},{k:"coffre",l:"Coffre"},{k:"appareils",l:"Appareils"},{k:"keys",l:"API keys"},') == 1, "")
check("2.2 'diag' dans la liste blanche des sections (sinon ?section=diag retombe sur accounts)", s.count('const ym=["diag","coffre","appareils","keys",') == 1, "")
check("2.3 la branche du corps rend DzDiag, apres Pricing, avant Transfert",
      s.count('s==="pricing"&&r.jsx(DzPricing,{}),s==="diag"&&r.jsx(DzDiag,{}),s==="coffre"&&r.jsx(DzCoffre,{}),s==="appareils"&&r.jsx(DzAppair,{}),s==="transfert"') == 1, "")
check("2.4 DzDiag appelle les deux routes du routeur /api/reglages, et seulement elles",
      s.count("fetch('/api/reglages/diagnostic')") == 1
      # #17 (29/09) : DzTestCle (ecran des cles) appelle aussi /diagnostic/cle -- on compte DANS DzDiag
      and s[s.find("function DzDiag("):s.find("function DzPricing(")].count("fetch('/api/reglages/diagnostic/cle',{method:'POST'") == 1, "")
_dz = s[s.find("function DzDiag("):s.find("function DzPricing(")]
check("2.5 le test de cle n'envoie que le NOM, dans le bundle LIVRE (la cle est relue cote serveur)",
      _dz.count("body:JSON.stringify({nom:k})})") == 1 and "valeur" not in _dz, "")
import re as _re                                              # noqa: E402
# #20 : la section porte aussi DzMaj et DzCoffre (des `title:` hors boutons) -> chaque bouton K, lu jusqu'a ses enfants
_ks = _re.findall(r"r\.jsx\(K,\{(.*?)children:", SEC["P2dg1-bloc-dzdiag-avant-dzpricing"][1])
check("2.6 tout bouton porte un title (E-12)", _ks and all("title:" in k for k in _ks), str(len(_ks)))
check("2.7 fins de ligne : 100 % CRLF", raw.count(b"\n") == raw.count(b"\r\n"), _d(raw.count(b"\n"), raw.count(b"\r\n")))
nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("2.8 node --check du bundle entier", nc is not None and nc.returncode == 0, _d(nc.stderr[-300:] if nc else ""))

print("\n[3] dzOct sous node")
i = s.find("function dzOct(")
j = s.find("function DzDiag(", i)
src = s[i:j] if 0 <= i < j else ""
p = pathlib.Path(tempfile.mkdtemp()) / "o.js"
p.write_text(src + "\nprocess.stdout.write(JSON.stringify([0,1023,1024,1536,10*1024*1024,14855500770,'x',null].map(dzOct)))", encoding="utf-8")
r = subprocess.run([NODE, str(p)], capture_output=True, text=True, encoding="utf-8")
try:
    out = json.loads(r.stdout)
except Exception:                                             # noqa: BLE001
    out = None
check("3.1 octets lisibles (virgule decimale, unites o/Ko/Mo/Go)",
      out == ["0 o", "1023 o", "1,0 Ko", "1,5 Ko", "10,0 Mo", "13,8 Go", "0 o", "0 o"], _d(out, r.stderr[-200:]))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
