"""Banc t181 (11/10/2026) : les liens de l'application vers le guide v3 arrivent sur un chapitre EXISTANT, dans la langue
de l'application.

  [B] le maillon de queue scripts/patch_bundle_dzguide.py dans le bundle livré : quatre liens « Guide » de l'onglet
      Assets 2D vers /guide/#<chapitre>, plus aucun lien en dur vers fr.html, marqueur unique, node --check ;
  [I] l'inverse avant_dzguide (backend/tests/_i18n_l1_aide.py) : aller-retour exact à l'octet, défait EN TÊTE de
      avant_i18nfix, double application refusée ;
  [G] le guide construit : chaque ancre visée existe dans fr.html ET en.html, la page /guide/ garde l'ancre en
      choisissant la langue, la commande « guide » du Vectorlab ouvre /guide/ et l'aide de l'Établi vise la langue de
      la page.

Run : & $PY backend/tests/test_guide_liens_app.py   (python embarqué, lanceur __main__)
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _i18n_l1_aide as A                                          # noqa: E402
import patch_bundle_dzguide as M                                   # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


BUN = RACINE / "frontend/dist/assets/index-BEOJX8L5.js"
B = BUN.read_bytes().decode("utf-8")
SOM = json.loads((RACINE / "docs/guide/src/chapitres.json").read_text("utf-8"))
IDS = {c["id"] for c in SOM["chapitres"]}

print("[B] le maillon dans le bundle livré")
liens = re.findall(r'g:"(/guide/[^"]*)"', B)
check("B1 quatre liens Guide, dans l'ordre des cartes",
      liens == ["/guide/#spritelab", "/guide/#tilelab", "/guide/#vectorlab-pixel", "/guide/#cardforge"], liens)
check("B2 plus aucun lien du bundle en dur vers une langue du guide", "/guide/fr.html" not in B and "/guide/en.html" not in B)
check("B3 marqueur unique", B.count(M.MARKER) == 1)
check("B4 aucun .bak_dzguide laissé", not BUN.with_name(BUN.name + ".bak_dzguide").exists())
r = subprocess.run(["node", "--check", str(BUN)], capture_output=True)
check("B5 node --check", r.returncode == 0, r.stderr.decode("utf-8", "replace")[-200:])
check("B6 lecture et écriture du maillon en octets",
      "read_bytes()" in (RACINE / "scripts/patch_bundle_dzguide.py").read_text("utf-8")
      and "write_bytes(" in (RACINE / "scripts/patch_bundle_dzguide.py").read_text("utf-8"))

print("\n[I] l'inverse")
sans = A.avant_dzguide(B)
check("I1 avant_dzguide défait les paires : plus de marqueur, l'ancien lien revient",
      M.MARKER not in sans and 'g:"/guide/fr.html#c18"}' in sans and sans.count('o:vl,g:""}') == 1)
check("I2 l'aller-retour est exact à l'octet (vu d'avant encartsia, t183, posé après)", M.appliquer(sans) == A.avant_encartsia(B))
check("I3 avant_i18nfix défait D'ABORD dzguide (posé après lui)", M.MARKER not in A.avant_i18nfix(B))
check("I4 un bundle sans le maillon passe tel quel", A.avant_dzguide(sans) == sans)
r = subprocess.run([sys.executable, str(RACINE / "scripts/patch_bundle_dzguide.py"), "--check"], capture_output=True,
                   text=True, cwd=str(RACINE))
check("I5 double application refusée", r.returncode != 0 and "double application" in (r.stdout + r.stderr), r.stdout + r.stderr)

print("\n[G] le guide construit")
for lang in ("fr", "en"):
    h = (RACINE / "docs/guide" / f"{lang}.html").read_text("utf-8")
    vises = [l.split("#", 1)[1] for l in liens]
    check(f"G1 [{lang}] chaque ancre visée est un chapitre publié",
          all(v in IDS and f'<section class="chapitre" id="{v}"' in h for v in vises), vises)
idx_js = re.search(r"<script>(.*?)</script>", (RACINE / "docs/guide/index.html").read_text("utf-8"), re.S).group(1)
res = []
for stocke, nav in (("en", "fr-FR"), ("fr", "en-US"), (None, "en-GB")):
    code = ("var out=null;var location={hash:'#spritelab',replace:function(u){out=u}};var navigator={language:'" + nav + "'};"
            "var localStorage={getItem:function(k){return k==='dz_lang'?" + json.dumps(stocke) + ":null}};"
            + idx_js + "console.log(out);")
    p = pathlib.Path(tempfile.mkdtemp(prefix="dzguide_")) / "idx.js"
    p.write_text(code, "utf-8")
    res.append(subprocess.run(["node", str(p)], capture_output=True, text=True).stdout.strip())
check("G2 /guide/#spritelab ouvre la langue de l'app (dz_lang, sinon navigateur) en gardant l'ancre",
      res == ["en.html#spritelab", "fr.html#spritelab", "en.html#spritelab"], res)
vl = (RACINE / "frontend/vectorlab/js/mod-charpente.js").read_text("utf-8")
check("G3 la commande « guide » du Vectorlab ouvre /guide/ (qui choisit la langue)",
      'window.open("/guide/", "_blank")' in vl)
aide = (RACINE / "frontend/etabli/aide.js").read_text("utf-8")
check("G4 l'aide de l'Établi vise /guide/<langue de la page>.html", "/guide/" in aide and "lang" in aide)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
