# -*- coding: utf-8 -*-
"""t141 (08/10/2026) — traduction L1 : la coque, la navigation, les Réglages et la Bibliothèque passent par dzT(clé)
(plan docs/superpowers/plans/2026-10-08-traduction-l1-coque-reglages-bibliotheque.md, skill traduction-deepotus).

  [1] la saisie et le générateur : scripts/i18n_l1_generer.py --check (table, couche, dictionnaires à jour).
  [2] le maillon patch_bundle_i18n_l1.py : octets ; REJEU — le bundle de BASE, couche MONTAGE rafraîchie depuis la
      source actuelle, puis le maillon, rend EXACTEMENT le bundle de référence ; double application refusée ; aucun .bak.
  [3] le dictionnaire : chaque dzT("coque.|reglages.|biblio.…") du bundle et de la couche existe, fr et en non vides,
      mêmes variables {x} des deux côtés ; dictionnaire assemblé à jour.
  [4] le runtime sous node : dzT rend le français et l'anglais des clés du lot, variables comprises.
  [5] plus de texte en dur dans le périmètre : le balayage lexical des composants du lot ne trouve plus de texte
      visible hors dzT, sauf les littéraux GARDÉS (motivés dans la saisie) et le bruit technique (CSS, valeurs).
  [6] compteurs figés (x.useState( 731, DzTracks 181), CRLF, node --check (script et module).
Run : & $PY tests/test_i18n_l1.py   (depuis backend/)
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
RACINE = HERE.parent.parent
REL = "frontend/dist/assets/index-BEOJX8L5.js"
# le bundle de référence : tant que t141 n'est pas commis, le bundle du poste ; une fois commis, épingler ici le commit
T141 = "c1addc0a"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


sys.path.insert(0, str(RACINE / "scripts"))
import i18n_l1_generer as G  # noqa: E402

BUNB = (RACINE / REL).read_bytes()
BUN = BUNB.decode("utf-8")
COUCHE = (RACINE / "frontend/patches/montage.js").read_bytes().decode("utf-8")
TABLE = json.loads((RACINE / "scripts/i18n_l1_paires.json").read_bytes().decode("utf-8"))

print("\n[1] la saisie et le générateur")
p = subprocess.run([sys.executable, str(RACINE / "scripts/i18n_l1_generer.py"), "--check"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=str(RACINE))
check("1a générateur --check : table, couche et dictionnaires à jour", p.returncode == 0, (p.stdout + p.stderr)[-400:])
check("1b la table porte la base et au moins 300 substitutions", TABLE.get("base") == G.BASE and len(TABLE["paires"]) >= 300,
      len(TABLE["paires"]))
check("1c chaque littéral gardé dit sa raison", all(g.get("raison") for g in TABLE["gardes"]))

print("\n[2] le maillon")
SCRIPT = RACINE / "scripts/patch_bundle_i18n_l1.py"
SRC = SCRIPT.read_bytes().decode("utf-8")
check("2a lecture et écriture en octets", "read_text(" not in SRC and "write_text(" not in SRC and "read_bytes()" in SRC)
eol = b"\r\n" if BUNB.count(b"\r\n") == BUNB.count(b"\n") else b"\n"
base = G.base("bundle")
entree = G.avec_couche(base, COUCHE)
if T141:
    reference = subprocess.run(["git", "show", f"{T141}:{REL}"], cwd=str(RACINE), capture_output=True).stdout
else:
    reference = BUNB
reference = reference.replace(b"\r\n", b"\n").replace(b"\n", eol)
TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzl1_"))
try:
    (TMP / "frontend/dist/assets").mkdir(parents=True)
    (TMP / "scripts").mkdir()
    shutil.copy(RACINE / "scripts/i18n_l1_paires.json", TMP / "scripts/i18n_l1_paires.json")
    (TMP / REL).write_bytes(entree.encode("utf-8"))
    r1 = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True, encoding="utf-8", errors="replace")
    rejoue = (TMP / REL).read_bytes()
    check("2b rejeu : base + couche rafraîchie + maillon = bundle de référence, octet pour octet",
          r1.returncode == 0 and rejoue == reference, (r1.returncode, (r1.stdout + r1.stderr)[-300:], len(rejoue), len(reference)))
    check("2c aucun .bak laissé", not list((TMP / "frontend/dist/assets").glob("*.bak_*")))
    r2 = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("2d second passage refusé (double application)", r2.returncode != 0 and "double application" in r2.stdout + r2.stderr
          and (TMP / REL).read_bytes() == rejoue, (r2.stdout + r2.stderr)[-200:])
finally:
    shutil.rmtree(TMP, ignore_errors=True)
check("2e aucun .bak_i18nl1 dans le dépôt", not (RACINE / (REL + ".bak_i18nl1")).exists())
# les bancs des patchers AMONT contrôlent leurs sections sur le bundle d'avant la traduction (tests/_i18n_l1_aide.py) :
# cela n'a de sens que si la traduction se défait EXACTEMENT
sys.path.insert(0, str(HERE))
import _i18n_l1_aide as AIDE  # noqa: E402
try:
    check("2g la traduction se défait exactement : avant_i18n(bundle) == base, octet pour octet",
          AIDE.avant_i18n(BUN) == base, "écart")
    check("2h la couche d'avant se reconstruit exactement (sans git)",
          AIDE.couche_avant_i18n(COUCHE).replace("\r\n", "\n") == G.base("couche").replace("\r\n", "\n"))
except ValueError as e:
    check("2g la traduction se défait exactement", False, e)
check("2f la couche du poste est celle que le générateur produit (rien d'édité à la main)",
      COUCHE.replace("\r\n", "\n") == G.construire({c: G.base(c) for c in G.CIBLES})[1].replace("\r\n", "\n"))

print("\n[3] le dictionnaire")
# les SOURCES du dictionnaire (l'assemblé dz-i18n-dico.js en est la concaténation, contrôlée en 3f)
DICO = {}
for f in sorted((RACINE / "frontend/shared/i18n").glob("*.json")):
    DICO.update(json.loads(f.read_text("utf-8")))
cles = sorted(set(re.findall(r'dzT\("((?:coque|reglages|biblio)\.[a-z0-9_.]+)"', BUN))
              | set(re.findall(r'dzT\("((?:coque|reglages|biblio)\.[a-z0-9_.]+)"', COUCHE)))
check("3a au moins 500 clés du lot sont utilisées", len(cles) >= 500, len(cles))
absentes = [c for c in cles if c not in DICO]
check("3b chaque clé utilisée est au dictionnaire assemblé", not absentes, absentes[:10])
vides = [c for c in cles if c in DICO and not (DICO[c].get("fr") and DICO[c].get("en"))]
check("3c fr et en non vides", not vides, vides[:10])
var = lambda t: sorted(set(re.findall(r"\{(\w+)\}", t)))      # noqa: E731
diff = [c for c in cles if c in DICO and var(DICO[c]["fr"]) != var(DICO[c]["en"])]
check("3d mêmes variables {x} en fr et en", not diff, [(c, DICO[c]) for c in diff[:5]])
inutiles = [c for c in DICO if c.split(".")[0] in ("coque", "reglages", "biblio") and c not in cles]
check("3e aucune clé du lot au dictionnaire sans usage", not inutiles, inutiles[:10])
p = subprocess.run([sys.executable, str(RACINE / "scripts/i18n_assembler.py"), "--check"], capture_output=True, text=True,
                   encoding="utf-8", errors="replace", cwd=str(RACINE))
check("3f dictionnaire assemblé à jour (i18n_assembler --check)", p.returncode == 0, (p.stdout + p.stderr)[-300:])

print("\n[4] le runtime sous node")
if NODE:
    HARNAIS = r"""
const fs = require("fs");
const [runPath, dicoPath, clesJson] = process.argv.slice(1);
const runSrc = fs.readFileSync(runPath, "utf8"), dicoSrc = fs.readFileSync(dicoPath, "utf8");
function monde(lang) {
  const magasin = { dz_lang: lang };
  const window = { location: { reload() {} } };
  window.localStorage = { getItem: k => (k in magasin ? magasin[k] : null), setItem: (k, v) => { magasin[k] = String(v); } };
  window.fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve({ ui_lang: lang }) });
  const document = { documentElement: { lang: "fr" }, readyState: "loading", addEventListener() {} };
  return new Function("window", "document", "localStorage", "MutationObserver", "Node", dicoSrc + "\n" + runSrc + "\n;return window;")(
    window, document, window.localStorage, undefined, { TEXT_NODE: 3, ELEMENT_NODE: 1 });
}
const fr = monde("fr"), en = monde("en"), R = {};
for (const c of JSON.parse(fs.readFileSync(clesJson, "utf8"))) R[c] = [fr.dzT(c, { n: 3, nom: "x.png" }), en.dzT(c, { n: 3, nom: "x.png" })];
// t141 : la surcouche ignore les entrées « contexte » (unités, Effacer de la Corbeille, Note = Rating…)
R.__surcouche = { To: en.__dzI18n.traduire("To"), Mo: en.__dzI18n.traduire("Mo"), Ko: en.__dzI18n.traduire(" Ko") };
R.__dzt_ctx = [en.dzT("reglages.unites.to"), en.dzT("biblio.corbeille.effacer"), en.dzT("biblio.meta.note")];
process.stdout.write(JSON.stringify(R));
"""
    t = pathlib.Path(tempfile.mkdtemp(prefix="dzl1n_"))
    (t / "cles.json").write_text(json.dumps(["reglages.cadre.titre", "reglages.onglet.cles", "coque.rail.library.label"] + cles[:40]), encoding="utf-8")
    r = subprocess.run([NODE, "-e", HARNAIS, str(RACINE / "frontend/dist/shared/dz-i18n.js"),
                        str(RACINE / "frontend/dist/shared/dz-i18n-dico.js"), str(t / "cles.json")],
                       capture_output=True, text=True, encoding="utf-8")
    shutil.rmtree(t, ignore_errors=True)
    R = json.loads(r.stdout) if r.returncode == 0 and r.stdout else {}
    check("4a le runtime rend « Réglages » / « Settings »", R.get("reglages.cadre.titre") == ["Réglages", "Settings"], R.get("reglages.cadre.titre"))
    S = R.pop("__surcouche", {})
    C = R.pop("__dzt_ctx", [])
    check("4c la surcouche IGNORE une entrée contextuelle (« To », « Mo », « Ko » ne deviennent pas TB / MB / KB à l'aveugle)",
          S == {"To": None, "Mo": None, "Ko": None}, S)
    check("4d dzT(clé) rend bien l'anglais d'une entrée contextuelle (TB, Delete, Rating)", C == ["TB", "Delete", "Rating"], C)
    check("4b chaque clé échantillonnée rend son fr et son en (jamais la clé elle-même)",
          all(v[0] != k and v[1] != k for k, v in R.items() if k in DICO), [k for k, v in R.items() if k in DICO and k in v][:5])
else:
    check("4- node présent", False, "node absent du PATH")

print("\n[5] plus de texte en dur dans le périmètre")
# le périmètre : les composants du lot dans le bundle (hors couche) et dans la couche
from i18n_l1_perimetre import restes  # noqa: E402
R5 = restes(BUN, COUCHE, TABLE["gardes"])
check("5a aucun texte visible en dur hors dzT dans le bundle (hors couche) du périmètre", not R5["bundle"], R5["bundle"][:15])
check("5b aucun texte visible en dur hors dzT dans la couche du périmètre", not R5["couche"], R5["couche"][:15])

print("\n[6] compteurs figés et syntaxe")
check("6a x.useState( 731, DzTracks 181 (dzT est une fonction globale, pas un hook)",
      BUN.count("x.useState(") == 731 and BUN.count("DzTracks") == 181, (BUN.count("x.useState("), BUN.count("DzTracks")))
check("6b fins de ligne intactes", BUNB.count(b"\r\n") == BUNB.count(b"\n") > 15000)
if NODE:
    r = subprocess.run([NODE, "--check", str(RACINE / REL)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("6c node --check (script)", r.returncode == 0, (r.stderr or "")[-300:])
    with (RACINE / REL).open("rb") as fh:
        r = subprocess.run([NODE, "--input-type=module", "--check"], stdin=fh, capture_output=True)
    check("6d node --check (module)", r.returncode == 0, (r.stderr or b"")[-300:])
idx = (RACINE / "frontend/dist/index.html").read_text("utf-8")
check("6e le runtime est chargé AVANT le bundle (dzT au chargement du module : liste du rail)",
      0 < idx.find("/shared/dz-i18n.js") < idx.find("/assets/index-BEOJX8L5.js"))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
