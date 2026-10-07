# -*- coding: utf-8 -*-
"""t129 (07/10/2026) — Quick, News et Épisodes gardent leur saisie à la navigation (scripts/patch_bundle_keepsaisie.py ;
spec docs/superpowers/specs/2026-08-06-preservation-etat-ecrans-design.md, étape 4).

  [1] le maillon : octets, parité, REJEU sur le bundle de main d'avant t129 → exactement le bundle commis ; second
      passage refusé ;
  [2] le bundle commis : chaque remplacement présent une fois, aucune ancre d'origine restante, le helper posé à côté
      du magasin de l'étape 1, aucun cycle de vie ajouté hors Quick (un useRef + un useEffect de démontage) ;
  [3] sous node : `__dzK` — une valeur conservée FAUSSE (null, 0, "", false) l'emporte sur le défaut, une clé absente
      rend le défaut ; la PRÉCÉDENCE de Quick (une recette extérieure prime sur l'état conservé), extraite du bundle et
      jouée avec des espions ; le miroir de News et d'Épisodes écrit toutes les clés relues par les initialiseurs ;
      la voix d'épisode conservée n'est plus écrasée par la liste des voix.
Run : & $PY tests/test_keepsaisie.py   (depuis backend/)
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
BASE = "90d93b6f"
REL = "frontend/dist/assets/index-BEOJX8L5.js"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


SRC = (RACINE / "scripts/patch_bundle_keepsaisie.py").read_bytes().decode("utf-8")
BUNB = (RACINE / REL).read_bytes()
BUN = BUNB.decode("utf-8")
sys.path.insert(0, str(RACINE / "scripts"))
try:
    import patch_bundle_keepsaisie as P
except Exception as e:
    P = None
    print(f"  (import du maillon impossible : {e!r})")

print("\n[1] le maillon")
check("1a_octets_et_parite", "read_text(" not in SRC and P is not None and P.deltas() == (P.SPEC_CHAR_DELTA, P.SPEC_BYTE_DELTA) == (1351, 1351))
base = subprocess.run(["git", "show", f"{BASE}:{REL}"], cwd=str(RACINE), capture_output=True).stdout
TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzkeep_"))
try:
    (TMP / "frontend/dist/assets").mkdir(parents=True)
    eol = b"\r\n" if BUNB.count(b"\r\n") == BUNB.count(b"\n") else b"\n"
    (TMP / REL).write_bytes(base.replace(b"\r\n", b"\n").replace(b"\n", eol))
    r1 = subprocess.run([sys.executable, str(RACINE / "scripts/patch_bundle_keepsaisie.py")], cwd=str(TMP),
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    # référence FIGÉE : l'empreinte git (blob, forme LF) du bundle livré par t129 — un maillon posé plus tard ne la
    # change pas (comparer au bundle COURANT rougirait à la première PR suivante : mesuré sur test_assets2d_lanceur).
    import hashlib
    lf = (TMP / REL).read_bytes().replace(b"\r\n", b"\n")
    check("1b_rejeu_rend_le_bundle_livre_octet_pour_octet", len(base) > 1_000_000 and r1.returncode == 0
          and hashlib.sha1(b"blob %d\x00" % len(lf) + lf).hexdigest() == "7d0cf76542b49f8597c0ca514ab7a165a5ae7bed",
          (r1.returncode, (r1.stdout + r1.stderr)[-300:]))
    (TMP / (REL + ".bak_keepsaisie")).unlink(missing_ok=True)
    r2 = subprocess.run([sys.executable, str(RACINE / "scripts/patch_bundle_keepsaisie.py")], cwd=str(TMP),
                        capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("1c_double_application_refusee", r2.returncode != 0 and "double application" in (r2.stdout + r2.stderr))
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("\n[2] le bundle commis")
if P is not None:
    manque = [t for t, a, r, n in P.PATCHES if BUN.count(r) != 1]
    reste = [t for t, a, r, n in P.PATCHES if a not in r and BUN.count(a) != 0]
    check("2a_chaque_remplacement_present_une_fois", not manque, manque)
    check("2b_aucune_ancre_d_origine_restante", not reste, reste)
check("2c_helper_a_cote_du_magasin", BUN.count("var __dzG=null,__dzKeep={};function __dzK(k,d){") == 1)
check("2d_fins_de_ligne_intactes", BUNB.count(b"\r\n") > 15000 and BUNB.count(b"\r\n") == BUNB.count(b"\n"))
cles_lues = set(re.findall(r'__dzK\("((?:news|episodes)\.[A-Za-z]+)"', BUN))
cles_ecrites = set(re.findall(r'"((?:news|episodes)\.[A-Za-z]+)":', BUN))
check("2e_le_miroir_ecrit_toutes_les_cles_relues", len(cles_lues) == 19 and cles_lues == cles_ecrites,
      (sorted(cles_lues - cles_ecrites), sorted(cles_ecrites - cles_lues)))
check("2f_le_mode_de_chapitres_lu_et_ecrit", BUN.count('__dzK("chapitres.mode",null)') == 1 and BUN.count('__dzKeep["chapitres.mode"]=m;') == 1)

print("\n[3] sous node")
h0 = BUN.find("function __dzK(")
helper = BUN[h0:BUN.find("}", BUN.find("return", h0)) + 1] if h0 > 0 else ""
q0 = BUN.find("var dzApplyRef=x.useRef(null);")
q1 = BUN.find("x.useEffect(function(){var r0=null;", q0)
FIN_Q = 'window.removeEventListener("deepotus:quick-recipe",onR)}},[]);'
q2 = BUN.find(FIN_Q, q1)
quick = BUN[q0:q2 + len(FIN_Q)] if 0 < q0 < q1 < q2 else ""   # les deux effets ENTIERS (rangement, puis reprise)
PROBE = r"""
"use strict";
var __dzKeep = {};
__HELPER__
var out = {};
__dzKeep["a"] = null; __dzKeep["b"] = 0; __dzKeep["c"] = ""; __dzKeep["d"] = false;
out.faux = [__dzK("a", 7), __dzK("b", 7), __dzK("c", 7), __dzK("d", 7), __dzK("absent", 7)];
// Quick : la tranche réelle du bundle, avec des espions pour les hooks et la recette
function joue(externe, conserve) {
  __dzKeep["quick.recette"] = conserve; var appliques = [], effets = [], refs = [];
  var x = {useRef: function (v) { var r = {current: v}; refs.push(r); return r; }, useEffect: function (f) { effets.push(f); }};
  var window = {__dzQuickRecipe: externe, addEventListener: function () {}, removeEventListener: function () {}};
  var dzQuickApply = function (rc) { appliques.push(rc); }, dzQuickRecipe = function () { return {tab: "courant"}; };
  (function () { __QUICK__ var fin = 1; }).call(null);
  return {appliques: appliques, effets: effets};
}
var a = joue({tab: "externe"}, {tab: "conserve"}); a.effets.forEach(function (f) { try { f(); } catch (_e) {} });
out.externe_prime = a.appliques;
var b = joue(undefined, {tab: "conserve"}); b.effets.forEach(function (f) { try { f(); } catch (_e) {} });
out.conserve = b.appliques;
var c = joue(undefined, {tab: "conserve"}); var nettoyages = c.effets.map(function (f) { try { return f(); } catch (_e) { return null; } });
nettoyages.forEach(function (g) { if (typeof g === "function") g(); });
out.range_au_demontage = __dzKeep["quick.recette"];
console.log(JSON.stringify(out));
"""
D = {}
if NODE and helper and quick:
    js = PROBE.replace("__HELPER__", helper).replace("__QUICK__", quick.replace("var dzApplyRef", "var dzApplyRef"))
    f = pathlib.Path(tempfile.mkdtemp(prefix="dzkeepn_")) / "k.js"
    f.write_text(js, encoding="utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    try:
        D = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("  (node :", (r.stderr or r.stdout)[-400:], ")")
    shutil.rmtree(f.parent, ignore_errors=True)
check("3a_tranches_extraites_et_jouees", bool(D), (len(helper), len(quick)))
if D:
    check("3b_une_valeur_conservee_fausse_l_emporte_sur_le_defaut", D["faux"] == [None, 0, "", False, 7], D["faux"])
    check("3c_la_recette_exterieure_prime_sur_l_etat_conserve", D["externe_prime"] == [{"tab": "externe"}], D["externe_prime"])
    check("3d_sans_recette_exterieure_l_etat_conserve_est_rejoue", D["conserve"] == [{"tab": "conserve"}], D["conserve"])
    check("3e_la_recette_courante_est_rangee_au_demontage", D["range_au_demontage"] == {"tab": "courant"}, D["range_au_demontage"])
check("3f_la_liste_des_voix_ne_remplit_qu_une_voix_vide",
      BUN.count("setVid(function(c0){return c0||g.voice_id})") == 1 and BUN.count("setVid(g.voice_id)") == 0)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
