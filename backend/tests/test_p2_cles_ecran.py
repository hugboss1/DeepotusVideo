# -*- coding: utf-8 -*-
"""Tache #17 (plan Settings T9, 29/09/2026) — L'ECRAN DES CLES dans le bundle (sections P2cl1..P2cl7, groupe P1 du
maillon montage) : un lien « Guide » et un bouton « Tester » par ligne, et plus aucun « restart the backend » (le
serveur applique la cle a chaud depuis T8 et son message dit la verite). Temoin : le bundle de la base 1656085.
dzChargerGuides est EXECUTEE sous node (un seul appel pour tout l'ecran, cache relache apres un echec).
Run : & $PY tests/test_p2_cles_ecran.py   (depuis backend/)"""
import json, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "scripts"))
import patch_bundle_montage as P                              # noqa: E402

BASE = "1656085"
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
SEC = {t: (a, r) for t, a, r in P.PATCHES if t.startswith("P2cl")}

print("\n[0] temoin : le bundle de la base (%s)" % BASE)
check("0.1 TEMOIN : ni DzTestCle ni guides ; les deux messages et l'aide promettent un redemarrage",
      vieux.count("function DzTestCle(") == 0 and vieux.count("/api/reglages/guides") == 0
      and vieux.count("restart the backend to apply") == 2 and vieux.count("pydantic-settings re-reads the file") == 1
      and vieux.count("Then in a PowerShell window") == 1, "")

print("\n[1] les sept sections")
_TAGS = [t for t, _a, _r in P.PATCHES]
_I = _TAGS.index(list(SEC)[0]) if SEC and list(SEC)[0] in _TAGS else -1
# #31 : repéré par POSITION du groupe, pas par un indice négatif figé — ne le suivent que P2rc1 puis le lot P3
check("1.1 treize sections P2cl, contiguës, en QUEUE de PATCHES (suivies seulement de P2rc1 puis du lot P3)", len(SEC) == 13
      and _I >= 0 and _TAGS[_I:_I + 13] == list(SEC) and _TAGS[_I + 13].startswith("P2rc1")
      and all(t.startswith(("P3", "P5", "P7", "P8", "P9")) for t in _TAGS[_I + 14:]), _d(list(SEC)))   # + P9lib (tache #77, 03/10) ; + P5qr (tache #48, 01/10)
for t, (a, r) in SEC.items():
    check(f"1.x {t} : ancre x1 dans .bak_montage, touchee par aucune autre section, remplacement x1 livre, sans saut de ligne",
          bak.count(a) == 1 and sum(1 for t2, a2, r2 in P.PATCHES if t2 != t and (a in a2 or a in r2)) == 0
          and s.count(r) == 1 and "\n" not in r and "\r" not in r, _d(bak.count(a), s.count(r)))

print("\n[2] l'ecran dans le bundle livre")
import re as _re
_rest = [s[max(0, m.start() - 160):m.start()] for m in _re.finditer(r"(?i)restart the backend", s)]
check("2.1 plus aucune promesse de redemarrage APRES un enregistrement par l'interface : ne restent que les deux "
      "bandeaux qui disent d'EDITER backend/.env a la main (vrai : une edition manuelle exige un redemarrage)",
      len(_rest) == 2 and all("backend/.env" in x for x in _rest) and "pydantic-settings re-reads" not in s
      and "Then in a PowerShell window" not in s and "Stop-Process -Force" not in s and vieux.lower().count("restart the backend") == 10,
      _d(len(_rest), vieux.lower().count("restart the backend")))
check("2.1b l'Ollama local affiche le message du serveur ; X, Telegram et « Connected accounts » disent « no restart »",
      s.count('f(h.message||"Saved — applied right away.")') == 1 and s.count(' Applied as soon as you save — no restart.",fields:[{k:"') == 2
      and s.count("the adapter is active right away, no restart.") == 1 and s.count('children:"save the keys first"}') == 1, "")
check("2.2 la ligne de cle a cinq colonnes, DzTestCle juste apres la pastille set/missing",
      s.count('gridTemplateColumns:"180px minmax(0,1fr) auto auto auto",gap:14') == 1 and s.count('style:{width:"100%",minWidth:0,boxSizing:"border-box",background:"var(--bg-base)",') == 1
      and s.count('children:h&&h.set===null?"coffre":h&&h.set?"set":"missing"}),r.jsx(DzTestCle,{ck:k.k,def:!!(h&&h.set),verrou:!!(h&&h.set===null)}),r.jsx(K,{') == 1, "")
check("2.3 les deux messages d'enregistrement affichent celui du SERVEUR (applique / redemarrage pour …)",
      s.count("f(p.message||`${k} enregistrée.`)") == 1 and s.count("f(c.message||`${") == 1, "")
dz = s[s.find("function DzTestCle("):s.find("const Fu=[{k:\"FAL_KEY\"")]
check("2.4 DzTestCle n'appelle que le test de #15, en n'envoyant que le NOM (la cle est relue cote serveur)",
      dz.count("fetch('/api/reglages/diagnostic/cle',{method:'POST'") == 1 and dz.count("body:JSON.stringify({nom:ck})") == 1
      and dz.count("fetch(") == 1 and "valeur" not in dz, "")
check("2.5 Tester seulement si la cle est posee ET a un guide (donc testable) ; Guide = lien console + tarifs en info-bulle",
      dz.count("gu&&def_?r.jsx(K,{") == 1 and dz.count("gu?r.jsx('a',{href:gu.console,target:'_blank',rel:'noreferrer'") == 1
      and dz.count("gu.tarifs") == 2, "")
r1 = SEC["P2cl1-dztestcle-avant-l-ecran-des-cles"][1]
check("2.6 tout bouton porte un title (E-12)", r1.count("r.jsx(K,{") == r1.count("title:'Appel authentifié") == 1, "")
check("2.7 le catalogue des cles reste lisible d'un tenant (`const Fu=[…];function bm(){`, rangee Figma de P1fg1)",
      s.count('health:"figma_configured"}];function bm(){') == 1, "")
check("2.8 fins de ligne : 100 % CRLF", raw.count(b"\n") == raw.count(b"\r\n"), "")
nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("2.9 node --check du bundle entier", nc is not None and nc.returncode == 0, _d(nc.stderr[-300:] if nc else ""))

print("\n[3] dzChargerGuides sous node")
i, j = s.find("var dzGuides=null"), s.find("function DzTestCle(")
src = s[i:j] if 0 <= i < j else ""
H = src + r"""
let n = 0, echoue = true;
globalThis.fetch = async u => { n++; if (echoue) throw new Error('reseau'); return { ok: true, json: async () => ({ guides: { FAL_KEY: { console: 'https://x' } } }) }; };
(async () => {
  const a = await dzChargerGuides();
  echoue = false;
  const b = await dzChargerGuides(), c = await dzChargerGuides();
  process.stdout.write(JSON.stringify({ a, b, c, n, cache: dzGuides }));
})();
"""
p = pathlib.Path(tempfile.mkdtemp()) / "g.js"
p.write_text(H, encoding="utf-8")
r = subprocess.run([NODE, str(p)], capture_output=True, text=True, encoding="utf-8") if NODE and src else None
try:
    o = json.loads(r.stdout) if r else {}
except Exception:                                             # noqa: BLE001
    o = {"erreur": (r.stdout + r.stderr)[-300:] if r else "rien"}
check("3.1 un echec reseau rend {} SANS figer le cache ; ensuite UN seul appel sert tout l'ecran",
      o.get("a") == {} and o.get("b") == o.get("c") == {"FAL_KEY": {"console": "https://x"}} and o.get("n") == 2
      and o.get("cache") == o.get("b"), _d(o))

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
